import logging
import autoshell
import json

log = logging.getLogger("modules")


def run(ball):
    submod = "guestshell.run"
    log.debug(f"{submod}: Starting the guestshell module")
    queue = autoshell.common.autoqueue.autoqueue(10, connect, None)
    for host in ball.hosts.ready_hosts():
        queue.put(host)
    queue.block()
    log.debug(f"{submod}: Done! Returning control to the AutoShell core")


def connect(parent, host):
    submod = "guestshell.connect"
    # Connect to host.
    log.info(f"{submod}: connecting to ({host.hostname})")
    connection = host.connections["cli"].connection
    connection.global_delay_factor = 20
    log.info(f"{submod}: starting worker on ({host.hostname})")
    worker(connection, host)


def status(connection, host):
    submod = "guestshell.status"
    response = connection.send_command("show guestshell | json")
    # If guestshell not created yet, return None (to quit).
    if response == "":
        return None

    # If guestshell is created, parse and return data.
    log.debug(f"{submod}: response data from ({host.hostname}): {response}")
    json_data = json.loads(response)["TABLE_detail"]["ROW_detail"]
    log.debug(f"{submod}: JSON data from ({host.hostname}): {json_data}")
    state = json_data["state"]
    rootfs = json_data["disk_reservation"]
    mem = json_data["memory_reservation"]
    cpu = json_data["cpu_reservation"]
    log.info(f"{submod}: guestshell on ({host.hostname}) is {state} with {cpu}% CPU, {mem} memory, {rootfs} disk space")
    return rootfs, mem, cpu, state


def resize(connection, host, rootfs, mem, cpu):
    submod = "guestshell.resize"
    # Check/resize rootfs reservation.
    if int(rootfs) < 1024:
        log.info(f"{submod}: Resizing rootfs reservation on ({host.hostname}), was ({rootfs})")
        response = connection.send_command("guestshell resize rootfs 1024")
    else:
        log.debuinfog(f"{submod}: rootfs reservation on ({host.hostname}) is sufficient, current ({rootfs})")
    
    # Check/resize memory reservation.
    if int(mem) < 1024:
        log.info(f"{submod}: Resizing memory reservation on ({host.hostname}), was ({mem})")
        response = connection.send_command("guestshell resize memory 1024")
    else:
        log.info(f"{submod}: memory reservation on ({host.hostname}) is sufficient, current ({mem})")

    # Check/resize CPU reservation.
    if int(cpu) < 5:
        log.info(f"{submod}: Resizing CPU reservation on ({host.hostname}), was ({cpu}%)")
        response = connection.send_command("guestshell resize cpu 5")
    else:
        log.info(f"{submod}: CPU reservation on ({host.hostname}) is sufficient, current ({cpu})")

def reboot(connection, host, state):
    submod = "guestshell.reboot"
    # Reboot the guest shell.
    # MOVE TO "REBOOT" FUNCTION.
    if state.lower() == "activated":
        log.info(f"{submod}: guestshell on ({host.hostname}) is active, rebooting")
        response = connection.send_command("guestshell reboot", expect_string="(y/n)")
        response = connection.send_command_timing("y")
        return True
    if state.lower() == "deactivated":
        log.info(f"{submod}: guestshell on ({host.hostname}) is deactivated, enabling")
        response = connection.send_command("guestshell enable")
        return True
    if "ing" in state.lower():
        log.info(f"{submod}: guestshell on ({host.hostname}) is busy, doing nothing")
        return False


def inet(connection, host):
    submod = "guestshell.inet"
    # Check internet reachability.
    response = connection.send_command("guestshell run sudo chvrf management ping -c 1 9.9.9.9")
    if "100% packet loss" in response:
        log.info(f"{submod}: guestshell on ({host.hostname}) cannot reach the internet, configure an interface in 'management' VRF")
        return False
    else:
        log.info(f"{submod}: guestshell on ({host.hostname}) can reach the internet")
        return True


def dns(connection, host):
    submod = "guestshell.dns"
    # Check DNS.
    response = connection.send_command("guestshell run sudo chvrf management getent hosts quad9.com")
    if response != "":
        log.info(f"{submod}: DNS is working on ({host.hostname})")
        return True
    else:
        log.info(f"{submod}: DNS it not working on ({host.hostname}), adding nameserver to /etc/resolv.conf")
        connection.send_command("guestshell run sudo sh -c 'echo nameserver 9.9.9.9 > /etc/resolv.conf'")
        attempts = 0
        while attempts <= 3:
            attempts =+ 1
            response = connection.send_command("guestshell run sudo chvrf management getent hosts quad9.com")
            if response == "":
                log.info(f"{submod}: cannot resolve DNS issues on ({host.hostname})")
                return False
            else:
                log.info(f"{submod}: DNS is working on ({host.hostname})")
                return True


def dependencies(connection, host):
    submod = "guestshell.dependencies"
    # Check/add endpoint repo.
    response = connection.send_command("guestshell run yum repolist")
    if not "endpoint/7/x86_64" in response:
        log.info(f"{submod}: endpoint repo does not exist on ({host.hostname}), adding")
        response = connection.send_command("guestshell run sudo chvrf management yum -y install https://packages.endpoint.com/rhel/7/os/x86_64/endpoint-repo-1.9-1.x86_64.rpm")
        if response:
            log.info(f"{submod}: endpoint repo added to ({host.hostname})")
        else:
            return False
    else:
        log.info(f"{submod}: endpoint repo already exists on ({host.hostname})")

    # Check/add git.
    response = connection.send_command("guestshell run yum list installed | grep git")
    if "git.x86_64" not in response:
        log.info(f"{submod}: git not yet installed on ({host.hostname}), installing")
        response = connection.send_command("guestshell run sudo chvrf management yum -y install git")
        if response:
            log.info(f"{submod}: git installed on ({host.hostname})")
        else:
            return False
    else:
        log.info(f"{submod}: git is already installed on ({host.hostname})")
    
    # Check/add python3.
    response = connection.send_command("guestshell run yum list installed | grep python3")
    if "python3.x86_64" not in response:
        log.info(f"{submod}: python3 not yet installed on ({host.hostname}), installing")
        response = connection.send_command("guestshell run sudo chvrf management yum -y install python3")
        if response:
            log.info(f"{submod}: python3 installed on ({host.hostname})")
        else:
            return False
    else:
        log.info(f"{submod}: python3 is already installed on ({host.hostname})")
    
    # Upgrade pip.
    response = connection.send_command("guestshell run sudo chvrf management pip3 install --upgrade pip")
    if response:
        log.info(f"{submod}: pip3 upgraded on ({host.hostname})")
    else:
        return False

    # Check/install natsort python module.
    response = connection.send_command("guestshell run pip freeze")
    if "natsort" not in response:
        log.info(f"{submod}: natsort python3 module not yet installed on ({host.hostname}), installing")
        response = connection.send_command("guestshell run sudo chvrf management pip3 install natsort")
        if response:
            log.info(f"{submod}: installed natsort on ({host.hostname})")
        else:
            return False
    else:
        log.info(f"{submod}: natsort python module is already installed on ({host.hostname})")

    # Check/clone network-code repo.
    response = connection.send_command("guestshell run ls /bootflash/scripts/network-code")
    if "No such file or directory" in response:
        log.info(f"{submod}: network-code repo not cloned on ({host.hostname}), cloning")
        response = connection.send_command("guestshell run sudo chvrf management git clone https://github.com/derek-shnosh/network-code.git /bootflash/scripts/network-code/")
        if response:
            log.info(f"{submod}: cloned network-code repo on ({host.hostname})")
        else:
            return False

    return True


def nxos_aliases(connection, host):
    submod = "guestshell.nxos_aliases"
    # Create CLI aliases for CDP scripts.
    commands = """cli alias name cdpbr guestshell run python /bootflash/scripts/network-code/python/nxos-cdp-brief.py
cli alias name cdpdesc guestshell run python /bootflash/scripts/network-code/python/nxos-cdp-describe.py -i
cli alias name wr copy run start
cli alias name ipint show ip int brief
cli alias name intstat show interf status
cli alias name vlbr show vlan brief | i ^[0-9]"""
    commands = commands.split("\n")
    connection.config_mode()
    for command in commands:
        connection.send_command(command)


def worker(connection, host):
    submod = "guestshell.worker"
    # Check to see if guestshell should be resized.
    log.info(f"{submod}: checking status of guestshell on ({host.hostname})")
    response = status(connection, host)
    # If guestshell isn't yet created, send command to create and return None (to quit).
    if not response:
        log.info(f"{submod}: guestshell on ({host.hostname}) not enabled yet; enabling, run module again after some time")
        response = connection.send_command_timing("guestshell enable")
        return None
    rootfs = response[0]
    mem = response[1]
    cpu = response[2]
    state = response[3]
    if int(rootfs) < 1024 or int(mem) < 1024 or int(cpu) < 5:
        log.info(f"{submod}: guestshell on ({host.hostname}) needs to be resized")
        resize(connection, host, rootfs, mem, cpu)
        reboot(connection, host, state)
        log.info(f"{submod}: guestshell on ({host.hostname}) has benen resized, run module again after some time")
        return None

    # Check internet.
    log.info(f"{submod}: checking internet reachability on ({host.hostname})")
    response = inet(connection, host)
    if not response:
        return None

    # Check DNS.
    log.info(f"{submod}: checking DNS on ({host.hostname})")
    response = dns(connection, host)
    if response == False:
        return None

    # Check dependencies.
    log.info(f"{submod}: checking required dependencies on ({host.hostname})")
    response = dependencies(connection, host)
    if not response:
        log.info(f"{submod}: could not install one or more required dependencies on ({host.hostname})")
        return None

    # Configure NXOS CLI aliases.
    log.info(f"{submod}: configuring NXOS CLI aliases on ({host.hostname})")
    response = nxos_aliases(connection, host)

    # Finish & update base packages.
    log.info(f"{submod}: guestshell prepped on ({host.hostname}), run `guestshell run sudo chvrf management yum -y update` to update base packages")
    # response = connection.send_command_timing("guestshell run sudo chvrf management yum -y update")
