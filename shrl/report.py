"""This module implements report accumulation and printing"""
import collections
import typing as ty

import tabulate


class FsSeq(ty.NamedTuple):
    gene: str
    positions: ty.List[int]


_frameshift_sequences: ty.List[FsSeq] = list()


def frameshift(gene: str, positions: ty.List[int]) -> None:
    _frameshift_sequences.append(FsSeq(gene=gene, positions=positions))


_entity_counts: ty.MutableMapping[str, int] = collections.Counter()


def count_entities(entities: ty.Mapping[str, ty.List[ty.Any]]) -> None:
    for name, ents in entities.items():
        _entity_counts[name] += len(ents)


Item = ty.Union[str, int, float]
Table = ty.List[ty.Mapping[str, Item]]
Report = ty.Mapping[str, Table]


def compile() -> Report:
    return {
        "Frameshifts": [fs._asdict() for fs in _frameshift_sequences],
        "Entities": [{"Entity Name": k, "Count": v} for k, v in _entity_counts.items()],
    }


def print_report() -> None:
    for name, data in compile().items():
        if len(data) == 0:
            continue
        print("-" * 69)
        print(f"-- {name}:")
        print(tabulate.tabulate(data, headers="keys"))
        print("\n")
