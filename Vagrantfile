# canaryd
# File: Vagrantfile
# Desc: canaryd test VM's


Vagrant.configure('2') do |config|
    # Disable /vagrant synced folder
    config.vm.synced_folder '.', '/vagrant', disabled: true

    # Copy canaryd to the VM
    config.vm.synced_folder './', '/opt/canaryd'

    # Begin canaryd test VM's:
    #

    # upstart
    config.vm.define :ubuntu14 do |ubuntu|
        ubuntu.vm.box = 'bento/ubuntu-14.04'
    end

    # systemd
    config.vm.define :ubuntu16 do |ubuntu|
        ubuntu.vm.box = 'bento/ubuntu-16.04'
    end

    # init.d
    config.vm.define :debian7 do |debian|
        debian.vm.box = 'bento/debian-7'
    end

    # ??? (systemd)
    config.vm.define :debian8 do |debian|
        debian.vm.box = 'bento/debian-8'
    end

    # ??? (systemd)
    config.vm.define :debian9 do |debian|
        debian.vm.box = 'bento/debian-9'
    end

    # ??? (init.d) / python2.6
    config.vm.define :centos6 do |centos|
        centos.vm.box = 'bento/centos-6'
    end

    # systemd
    config.vm.define :centos7 do |centos|
        centos.vm.box = 'bento/centos-7'
    end

    # rc.d
    # config.vm.define :openbsd58 do |openbsd|
    #     openbsd.vm.box = 'twingly/openbsd-5.8-amd64'
    #     openbsd.vm.synced_folder './', '/opt/canaryd', type: 'rsync'
    # end
end
