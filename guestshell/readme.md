[autoshell]: https://github.com/PackeTsar/autoshell

# Guestshell Scripts

## `guestshell_prep.py`

[Autoshell][autoshell] script to prep the guestshell; i.e., resize CPU, memory and disk reservations.

Example usage;

```bash
autoshell -c admin:admin -m guestshell.py 10.0.0.61n@cisco_nxos -dd
```

## `guestshell_config.sh`

Bash script to configure DNS and update the underlying guestshell OS and install dependencies for CDP scripts