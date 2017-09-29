# canaryd

[Service Canary](https://servicecanary.com) daemon that collects and uploads system state.


## Development

Requires [Vagrant](https://vagrantup.com) & [pyinfra](https://github.com/Fizzadar/pyinfra) (>=0.5).

```sh
# Up the test VM's:
vagrant up

# Deploy the package in dev mode
pyinfra @vagrant deploy/install_dev.py
```
