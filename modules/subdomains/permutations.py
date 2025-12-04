PREFIXES = ["dev", "test", "staging", "old", "v2", "qa", "prod"]
SUFFIXES = ["dev", "test", "backup", "v2"]


def generate_permutations(subdomain):
    parts = subdomain.split(".")[0]
    results = []
    for p in PREFIXES:
        results.append(f"{p}.{subdomain}")
        results.append(f"{parts}-{p}.{subdomain}")
    for s in SUFFIXES:
        results.append(f"{parts}.{s}.{'.'.join(subdomain.split('.')[1:])}")
        results.append(f"{parts}-{s}.{'.'.join(subdomain.split('.')[1:])}")
    return results
