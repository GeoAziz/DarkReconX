import ipaddress


def cidr_to_ips(cidr):
    return set(str(ip) for ip in ipaddress.IPv4Network(cidr, strict=False))


def expand_targets(args):
    targets = set()

    if getattr(args, "domain", None):
        targets.add(args.domain)

    if getattr(args, "list", None):
        with open(args.list) as f:
            for line in f:
                line = line.strip()
                if line:
                    targets.add(line)

    if getattr(args, "cidr", None):
        targets |= cidr_to_ips(args.cidr)

    if getattr(args, "subs", None):
        with open(args.subs) as f:
            for line in f:
                line = line.strip()
                if line:
                    targets.add(line)

    # Deduplicate, sort, validate
    valid = set()
    for t in targets:
        t = t.strip()
        if t:
            valid.add(t)
    return sorted(valid)
