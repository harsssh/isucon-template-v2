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

  def test_copies_relative_symlinks_and_reports_no_change_on_retry
    write("#{@repo}/common/etc/nginx/sites-available/demo", 'server {}')
    FileUtils.mkdir_p("#{@repo}/common/etc/nginx/sites-enabled")
    File.symlink('../sites-available/demo', "#{@repo}/common/etc/nginx/sites-enabled/demo")

    changed = distribute

    assert_includes changed, "#{@root}/etc/nginx/sites-enabled/demo"
    assert_equal '../sites-available/demo', File.readlink("#{@root}/etc/nginx/sites-enabled/demo")
    assert_equal 'server {}', File.read("#{@root}/etc/nginx/sites-enabled/demo")
    assert_equal [], distribute
  end

  def test_host_symlink_overrides_common_file_and_preserves_absolute_target
    write("#{@repo}/common/etc/nginx/demo", 'common')
    distribute
    FileUtils.mkdir_p("#{@repo}/s1/etc/nginx")
    File.symlink('/etc/nginx/missing', "#{@repo}/s1/etc/nginx/demo")

    assert_equal ["#{@root}/etc/nginx/demo"], distribute
    assert_equal '/etc/nginx/missing', File.readlink("#{@root}/etc/nginx/demo")
    assert_equal [], distribute
  end

  def test_changes_symlink_target
    FileUtils.mkdir_p("#{@repo}/common/etc/nginx")
    File.symlink('first', "#{@repo}/common/etc/nginx/demo")
    distribute
    File.unlink("#{@repo}/common/etc/nginx/demo")
    File.symlink('second', "#{@repo}/common/etc/nginx/demo")

    assert_equal ["#{@root}/etc/nginx/demo"], distribute
    assert_equal 'second', File.readlink("#{@root}/etc/nginx/demo")
  end

  def test_file_replaces_symlink_without_overwriting_its_target
    write("#{@repo}/common/etc/nginx/demo", 'same')
    write("#{@root}/original", 'same')
    FileUtils.mkdir_p("#{@root}/etc/nginx")
    File.symlink("#{@root}/original", "#{@root}/etc/nginx/demo")

    assert_equal ["#{@root}/etc/nginx/demo"], distribute
    refute File.symlink?("#{@root}/etc/nginx/demo")
    assert_equal 'same', File.read("#{@root}/etc/nginx/demo")
    assert_equal 'same', File.read("#{@root}/original")
  end
end
