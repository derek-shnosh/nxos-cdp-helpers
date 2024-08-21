import logging
import autoshell
import json

log = logging.getLogger("modules")


def run(ball):
    log.debug("guestshell_config.run: Starting the guestshell_config module")
    queue = autoshell.common.autoqueue.autoqueue(10, connect, None)
    for host in ball.hosts.ready_hosts():
        queue.put(host)
    queue.block()
    log.debug("guestshell_config.run: Done! Returning control to the AutoShell core")


def connect(parent, host):
    # Connect to host.
    log.debug(f"guestshell_config.connect: connecting to ({host.hostname})")
    connection = host.connections["cli"].connection
    config(connection, host)


def config(connection, host):
    # Configure DNS.
    log.info(dir(connection))
    log.info(connection.global_delay_factor)
    log.info(f"guestshell_config.config: configuring DNS on ({host.hostname})")
    response = connection.send_command("guestshell run sudo sh -c 'echo nameserver 9.9.9.9 > /etc/resolv.conf'")

    # Update base system packages.
    log.info(f"guestshell_config.config: updating base system packages on ({host.hostname})")
    response = connection.send_command("guestshell run sudo chvrf management yum -y update")

    # Install git & python3.
    log.info(f"guestshell_config.config: installing git and python3 on ({host.hostname})")
    response = connection.send_command("guestshell run sudo chvrf management yum -y install https://packages.endpoint.com/rhel/7/os/x86_64/endpoint-repo-1.9-1.x86_64.rpm")
    response = connection.send_command("guestshell run sudo chvrf management yum -y install git python3")

    # Upgrade pip3.
    log.info(f"guestshell_config.config: upgrading pip3 on ({host.hostname})")
    response = connection.send_command("guestshell run sudo chvrf management pip3 install --upgrade pip")

    # Install natsort for python3.
    log.info(f"guestshell_config.config: installing natsort module on ({host.hostname})")
    response = connection.send_command("guestshell run sudo chvrf management pip3 install natsort")

    # Clone network-code repo.
    log.info(f"guestshell_config.config: cloning network-code repo on ({host.hostname})")
    response = connection.send_command("guestshell run sudo chvrf management git clone https://github.com/derek-shnosh/network-code.git /bootflash/scripts/network-code/")

    # Create cli aliases for CDP scripts.
    # !!! NEEDS FIXED
    # log.info(f"guestshell_config.config: creating cli aliases on ({host.hostname})")
    # response = connection.send_command("conf ; cli alias name cdpbr guestshell run python /bootflash/scripts/network-code/python/nxos-cdp-brief.py\nexit")
    # response = connection.send_command("conf ; cli alias name cdpdesc guestshell run python /bootflash/scripts/network-code/python/nxos-cdp-describe.py -i\nexit")
