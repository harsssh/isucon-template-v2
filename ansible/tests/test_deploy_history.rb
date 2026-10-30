require 'fileutils'
require 'json'
require 'minitest/autorun'
require 'open3'
require 'rbconfig'
require 'tmpdir'
require 'timeout'

class TestDeployHistory < Minitest::Test
  SCRIPT = File.expand_path('../deploy_history.rb', __dir__)

  def setup
    @repo = Dir.mktmpdir
    @bin = File.join(@repo, 'bin')
    FileUtils.mkdir_p(@bin)
    @env = {
      'PATH' => "#{@bin}:#{ENV.fetch('PATH')}",
      'GIT_CONFIG_GLOBAL' => File::NULL,
      'GIT_CONFIG_NOSYSTEM' => '1'
    }
    File.write(File.join(@repo, '.gitignore'), "bin/\n.deploy-history/\nready\n")
    command('git', 'init', '-q')
    command('git', 'add', '.gitignore')
    command('git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'initial')
    @sha = command('git', 'rev-parse', 'HEAD').strip
  end

  def teardown
    FileUtils.rm_rf(@repo)
  end

  def command(*args)
    stdout, stderr, status = Open3.capture3(@env, *args, chdir: @repo)
    assert status.success?, stderr
    stdout.force_encoding(Encoding::UTF_8)
  end

  def runner(source)
    File.write(File.join(@bin, 'ansible-playbook'), "#!#{RbConfig.ruby}\nrequire 'json'\n$stdout.sync = true\n#{source}")
    File.chmod(0o755, File.join(@bin, 'ansible-playbook'))
  end

  def event(host, metadata)
    {
      '_event' => 'v2_runner_on_ok',
      'hosts' => { host => { 'ansible_stats' => { 'data' => { 'deployment' => metadata } } } }
    }
  end

  def emit(events)
    events.map { |entry| "puts #{JSON.generate(entry).dump}" }.join("\n")
  end

  def history
    files = Dir.glob(File.join(@repo, '.deploy-history/*.json'))
    assert_equal 1, files.length
    JSON.parse(File.read(files.first))
  end

  def test_success_records_deployed_hosts_and_lists_history
    runner(emit([
      event('s1', { 'sha' => 'abc123', 'services' => ['nginx', 'app'], 'status' => 'running' }),
      event('s2', { 'sha' => 'abc123', 'services' => ['mysql'], 'status' => 'running' }),
      event('s1', { 'status' => 'succeeded' }),
      event('s2', { 'status' => 'succeeded' })
    ]))

    command(RbConfig.ruby, SCRIPT, 'deploy', 'feature-branch')

    record = history
    assert_equal 'succeeded', record['status']
    assert_equal 'feature-branch', record['branch']
    assert_equal({ 'sha' => @sha, 'dirty' => false }, record['controller'])
    assert_equal({ 'sha' => 'abc123', 'services' => ['mysql'], 'status' => 'succeeded' }, record['hosts']['s2'])
    refute_nil record['started_at']
    refute_nil record['finished_at']
    listing = command(RbConfig.ruby, SCRIPT, 'list')
    assert_includes listing, 'branch=feature-branch'
    assert_includes listing, 's2 succeeded sha=abc123 services=mysql'
  end

  def test_failure_records_task_without_storing_module_output
    File.write(File.join(@repo, 'uncommitted'), 'changed')
    failure = {
      '_event' => 'v2_runner_on_failed', 'task' => { 'name' => 'Validate nginx config' },
      'hosts' => { 's1' => { 'failed' => true, 'msg' => 'sensitive module output' } }
    }
    runner(emit([event('s1', { 'sha' => 'abc123', 'services' => ['nginx'] }), failure]) + "\nexit 2\n")

    _, _, status = Open3.capture3(@env, RbConfig.ruby, SCRIPT, 'deploy', chdir: @repo)

    assert_equal 2, status.exitstatus
    record = history
    assert_equal 'failed', record['status']
    assert record['controller']['dirty']
    assert_equal 'Validate nginx config', record['hosts']['s1']['failed_task']
    refute_includes JSON.generate(record), 'sensitive module output'
  end

  def test_startup_failure_records_failure_and_empty_history_is_readable
    assert_includes command(RbConfig.ruby, SCRIPT, 'list'), 'デプロイ履歴はありません'
    File.write(File.join(@bin, 'ansible-playbook'), "#!/nonexistent-interpreter\n")
    File.chmod(0o755, File.join(@bin, 'ansible-playbook'))

    _, _, status = Open3.capture3(@env, RbConfig.ruby, SCRIPT, 'deploy', chdir: @repo)

    assert_equal 127, status.exitstatus
    assert_equal 'failed', history['status']
    refute_nil history['finished_at']
  end

  def test_interruption_preserves_partial_host_record
    runner(emit([event('s1', { 'sha' => 'abc123', 'services' => ['app'], 'status' => 'running' })]) + "\nFile.write('ready', '')\nsleep 30\n")
    pid = Process.spawn(@env, RbConfig.ruby, SCRIPT, 'deploy', chdir: @repo, out: File::NULL, err: File::NULL)
    begin
      Timeout.timeout(10) do
        sleep 0.02 until File.exist?(File.join(@repo, 'ready'))
      end
      Process.kill('TERM', pid)
      _, status = Timeout.timeout(10) { Process.wait2(pid) }
      pid = nil

      refute status.success?
      record = history
      assert_equal 'interrupted', record['status']
      assert_equal 'abc123', record['hosts']['s1']['sha']
      assert_equal 'running', record['hosts']['s1']['status']
    ensure
      if pid
        Process.kill('TERM', pid)
        Process.wait(pid)
      end
    end
  end
end
