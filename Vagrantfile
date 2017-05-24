# canaryd
# File: Vagrantfile
# Desc: canaryd test VM's


Vagrant.configure('2') do |config|
    config.vm.box = 'ubuntu/trusty64'

    # Disable /vagrant synced folder
    config.vm.synced_folder '.', '/vagrant', disabled: true

    # Copy canaryd to the VM
    config.vm.synced_folder './', '/opt/canaryd', type: 'rsync'

    # Provision with pyinfra
    config.vm.provision :pyinfra do |pyinfra|
        pyinfra.deploy_file = 'deploy/install.py'
    end

    # Begin canaryd test VM's:
    #

    # upstart
    config.vm.define :ubuntu14 do |ubuntu|
        ubuntu.vm.box = 'ubuntu/trusty64'
    end

    # systemd
    config.vm.define :ubuntu15 do |ubuntu|
        ubuntu.vm.box = 'ubuntu/wily64'
    end

    # init.d
    config.vm.define :debian7 do |debian|
        debian.vm.box = 'debian/wheezy64'
    end

    # ??? (systemd)
    config.vm.define :debian8 do |debian|
        debian.vm.box = 'debian/jessie64'
    end

    # ??? (init.d) / python2.6
    config.vm.define :centos6 do |centos|
        centos.vm.box = 'centos/6'
    end

    # systemd
    config.vm.define :centos7 do |centos|
        centos.vm.box = 'centos/7'
    end

    # rc.d
    config.vm.define :openbsd58 do |openbsd|
        openbsd.vm.box = 'twingly/openbsd-5.8-amd64'
    end
end
