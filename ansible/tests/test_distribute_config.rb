require 'fileutils'
require 'minitest/autorun'
require 'open3'
require 'tmpdir'

SCRIPT = File.expand_path('../files/distribute_config.sh', __dir__)

class TestDistributeConfig < Minitest::Test
  def setup
    @repo = Dir.mktmpdir
    @root = Dir.mktmpdir
  end

  def teardown
    FileUtils.rm_rf([@repo, @root])
  end

  def write(path, content)
    FileUtils.mkdir_p(File.dirname(path))
    File.write(path, content)
  end

  def distribute(host = 's1')
    stdout, stderr, status = Open3.capture3(SCRIPT, host, @root, chdir: @repo)
    assert status.success?, stderr
    stdout.lines(chomp: true).sort
  end

  def test_copies_common_files
    write("#{@repo}/common/etc/nginx/nginx.conf", 'common')

    changed = distribute

    assert_equal ["#{@root}/etc/nginx/nginx.conf"], changed
    assert_equal 'common', File.read("#{@root}/etc/nginx/nginx.conf")
  end

  def test_host_files_take_precedence_over_common
    write("#{@repo}/common/etc/nginx/nginx.conf", 'common')
    write("#{@repo}/s1/etc/nginx/nginx.conf", 's1')

    distribute

    assert_equal 's1', File.read("#{@root}/etc/nginx/nginx.conf")
  end

  def test_ignores_other_hosts
    write("#{@repo}/s2/etc/nginx/nginx.conf", 's2')

    assert_equal [], distribute
    refute File.exist?("#{@root}/etc/nginx/nginx.conf")
  end

  def test_reports_nothing_when_unchanged
    write("#{@repo}/common/etc/nginx/nginx.conf", 'common')
    write("#{@repo}/s1/etc/nginx/nginx.conf", 's1')
    distribute

    assert_equal [], distribute
  end

  def test_reports_only_changed_files
    write("#{@repo}/common/etc/nginx/nginx.conf", 'v1')
    write("#{@repo}/common/etc/mysql/my.cnf", 'v1')
    distribute
    write("#{@repo}/common/etc/mysql/my.cnf", 'v2')

    assert_equal ["#{@root}/etc/mysql/my.cnf"], distribute
  end
end
