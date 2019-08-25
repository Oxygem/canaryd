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

    # systemd
    config.vm.define :ubuntu18 do |ubuntu|
        ubuntu.vm.box = 'bento/ubuntu-18.04'
    end

    # init.d
    config.vm.define :debian7 do |debian|
        debian.vm.box = 'bento/debian-7'
    end

    # systemd
    config.vm.define :debian10 do |debian|
        debian.vm.box = 'bento/debian-10'
    end

    # upstart / python2.6
    config.vm.define :centos6 do |centos|
        centos.vm.box = 'bento/centos-6'
    end

    # systemd
    config.vm.define :centos7 do |centos|
        centos.vm.box = 'bento/centos-7'
    end

    # rc.d
    config.vm.define :openbsd6 do |openbsd|
        openbsd.vm.box = 'ryanmaclean/openbsd-6.0'
    end
end
