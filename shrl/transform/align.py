import typing as ty


def profile_name(gt: str, subgt: ty.Optional[str]) -> str:
    "Choose a nucamino alignment profile based on genotype and subgenotype"
    GENOTYPES = {"1", "2", "3", "4", "5", "6"}
    if gt not in GENOTYPES:
        raise ValueError(f"Invalid Genotype: {gt}")
    if subgt is not None:
        if type(subgt) is not str or len(subgt) > 1:
            msg = f"Invalid subgenotype: {subgt}"
            raise ValueError(msg)
    if gt == "1":
        if subgt == "b":
            return "hcv1b"
        else:
            return "hcv1a"
    else:
        return f"hcv{gt}"
