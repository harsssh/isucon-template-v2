require 'fileutils'
require 'json'
require 'open3'
require 'securerandom'
require 'time'

module DeployHistory
  DIRECTORY = '.deploy-history'.freeze

  def self.record_event(record, event)
    hosts = event.fetch('hosts', {}).to_h do |name, result|
      previous = record.fetch('hosts').fetch(name, { 'status' => 'running' })
      metadata = result.dig('ansible_stats', 'data', 'deployment') || {}
      failure = case event['_event']
                when 'v2_runner_on_failed', 'v2_runner_on_unreachable'
                  { 'status' => 'failed', 'failed_task' => event.dig('task', 'name') }
                else
                  {}
                end
      [name, previous.merge(metadata.slice('sha', 'services', 'status')).merge(failure)]
    end
    record.merge('hosts' => record.fetch('hosts').merge(hosts))
  end

  def self.finished_record(record, exit_code, interrupted, finished_at)
    hosts = record.fetch('hosts')
    succeeded = exit_code == 0 && !hosts.empty? && hosts.values.all? { |host| host['status'] == 'succeeded' }
    status = interrupted ? 'interrupted' : succeeded ? 'succeeded' : 'failed'
    record.merge('status' => status, 'finished_at' => finished_at, 'exit_code' => exit_code)
  end

  def self.event_lines(event)
    case event['_event']
    when 'v2_playbook_on_task_start', 'v2_playbook_on_handler_task_start'
      ["TASK [#{event.dig('task', 'name')}]"]
    when 'v2_runner_on_ok', 'v2_runner_on_failed', 'v2_runner_on_unreachable', 'v2_runner_on_skipped'
      event.fetch('hosts', {}).map do |host, result|
        status = event['_event'].delete_prefix('v2_runner_on_')
        status = 'changed' if status == 'ok' && result['changed']
        details = %w[failed unreachable].include?(status) ? " #{JSON.generate(result)}" : ''
        "#{status}: [#{host}]#{details}"
      end
    else
      []
    end
  end

  def self.save(path, record)
    File.write("#{path}.tmp", JSON.pretty_generate(record) + "\n", mode: 'w', perm: 0o600)
    File.rename("#{path}.tmp", path)
  end

  def self.git_output(*args)
    output, status = Open3.capture2('git', '-c', 'core.fsmonitor=false', *args)
    raise "git #{args.join(' ')} failed" unless status.success?

    output.strip
  end

  def self.run(branch)
    started_at = Time.now.utc
    record = {
      'started_at' => started_at.iso8601,
      'finished_at' => nil,
      'branch' => branch,
      'controller' => {
        'sha' => git_output('rev-parse', 'HEAD'),
        'dirty' => !git_output('status', '--porcelain').empty?
      },
      'status' => 'running',
      'hosts' => {}
    }
    FileUtils.mkdir_p(DIRECTORY, mode: 0o700)
    path = File.join(DIRECTORY, "#{started_at.strftime('%Y%m%dT%H%M%SZ')}-#{SecureRandom.hex(4)}.json")
    save(path, record)
    puts "履歴: #{path}"
    $stdout.flush
    env = { 'ANSIBLE_STDOUT_CALLBACK' => 'ansible.posix.jsonl', 'ANSIBLE_JSON_INDENT' => '0', 'ANSIBLE_FORCE_COLOR' => '0' }
    reader, writer = IO.pipe
    begin
      pid = Process.spawn(env, 'ansible-playbook', 'ansible/deploy.yml', '-e', JSON.generate(branch:), out: writer, pgroup: true)
    rescue SystemCallError => error
      warn error.message
      save(path, finished_record(record, 127, false, Time.now.utc.iso8601))
      reader.close
      writer.close
      return 127
    end
    writer.close
    received_signal = nil
    handlers = %w[INT TERM].to_h do |signal|
      handler = Signal.trap(signal) do
        received_signal = signal
        begin
          Process.kill(signal, -pid)
        rescue Errno::ESRCH
          # 子プロセスが終了済みなら、受け取ったシグナルだけを記録する
        end
      end
      [signal, handler]
    end
    begin
      reader.each_line do |line|
        begin
          event = JSON.parse(line)
        rescue JSON::ParserError
          print line
          next
        end
        record = record_event(record, event)
        save(path, record)
        event_lines(event).each { |text| puts text }
        $stdout.flush
      end
      _, status = Process.wait2(pid)
      exit_code = status.exitstatus || 128 + status.termsig
      completed = finished_record(record, exit_code, !received_signal.nil? || status.signaled?, Time.now.utc.iso8601)
      save(path, completed)
      puts "結果: #{completed.fetch('status')} (#{path})"
      completed['status'] == 'succeeded' ? 0 : exit_code.zero? ? 1 : exit_code
    ensure
      reader.close
      handlers.each { |signal, handler| Signal.trap(signal, handler) }
    end
  end

  def self.list
    paths = Dir.glob(File.join(DIRECTORY, '*.json')).sort.reverse.first(20)
    puts 'デプロイ履歴はありません' if paths.empty?
    paths.each do |path|
      record = JSON.parse(File.read(path))
      puts "#{record.fetch('started_at')} #{record.fetch('status')} branch=#{record.fetch('branch')}"
      record.fetch('hosts').each do |host, result|
        puts "  #{host} #{result.fetch('status')} sha=#{result.fetch('sha', '-')} services=#{result.fetch('services', []).join(',')}"
        puts "    failed_task=#{result['failed_task']}" if result['failed_task']
      end
      puts "  #{path}"
    end
  end
end

if $PROGRAM_NAME == __FILE__
  case ARGV.shift
  when 'deploy'
    exit DeployHistory.run(ARGV.fetch(0, ENV.fetch('BRANCH', 'main')))
  when 'list'
    DeployHistory.list
  else
    abort 'Usage: ruby ansible/deploy_history.rb deploy [branch] | list'
  end
end
