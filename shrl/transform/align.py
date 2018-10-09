import typing as ty
import uuid

import pynucamino as pn

import shared_schema.reference_sequences as refseqs

from . import entities


def check_gt_and_subgt(gt: str, subgt: ty.Optional[str]) -> None:
    GENOTYPES = {"1", "2", "3", "4", "5", "6"}
    if gt not in GENOTYPES:
        raise ValueError(f"Invalid Genotype: {gt}")
    if subgt is not None:
        if type(subgt) is not str or len(subgt) > 1:
            msg = f"Invalid subgenotype: {subgt}"
            raise ValueError(msg)


def profile_name(gt: str, subgt: ty.Optional[str]) -> str:
    "Choose a nucamino alignment profile based on genotype and subgenotype"
    check_gt_and_subgt(gt, subgt)
    if gt == "1":
        if subgt == "b":
            return "hcv1b"
        else:
            return "hcv1a"
    else:
        return f"hcv{gt}"


RefseqKey = ty.Tuple[str, ty.Optional[str], refseqs.Gene]
REFSEQ_INDEX: ty.Dict[RefseqKey, uuid.UUID] = {
    (rs.genotype, rs.subgenotype, rs.gene): rs.shared_id for rs in refseqs.SEQS
}


def refseq_id(gt: str, subgt: ty.Optional[str], gene_src: str) -> uuid.UUID:
    check_gt_and_subgt(gt, subgt)
    gene = refseqs.Gene(gene_src.lower())
    key: ty.Tuple[str, ty.Optional[str], refseqs.Gene]
    if gt == "1":
        if subgt == "b":
            key = ("1", "b", gene)
        else:
            key = ("1", "a", gene)
    else:
        key = (gt, None, gene)
    refseq = REFSEQ_INDEX[key]
    return refseq


def ensure_fasta_formatted(seq_str: str, hdr: str = "Reformatted") -> str:
    TMPL = "> {hdr}\n{seq}"
    if not seq_str.startswith(">"):
        return TMPL.format(hdr=hdr, seq=seq_str)
    else:
        return seq_str


def alignment(
    sequence: entities.Sequence, gene: str, aln_report: ty.Any, notes: str = ""
) -> entities.Alignment:
    nt_start = aln_report["FirstNA"]
    nt_end = aln_report["LastAA"]
    ref_seq = refseq_id(sequence.genotype, sequence.subgenotype, gene)
    return entities.Alignment(
        id=uuid.uuid4(),
        sequence_id=sequence.id,
        reference_id=ref_seq,
        nt_start=nt_start,
        nt_end=nt_end,
        gene=gene,
    )


def substitution(
    alignment: entities.Alignment,
    mtn: ty.Any,  # One mutation object from the Nucamino alignment report
) -> entities.Substitution:
    specific_fields: ty.Dict[str, ty.Any] = {
        "sub_aa": None,
        "insertion": None,
        "deletion_length": None,
    }
    if mtn["IsInsertion"]:
        kind = "insertion"
        specific_fields["insertion"] = mtn["InsertedAminoAcidsText"]
    elif mtn["IsDeletion"]:
        kind = "deletion"
        specific_fields["deletion_length"] = len(mtn["Control"]) // 3
    else:
        kind = "simple"
        specific_fields["sub_aa"] = mtn["AminoAcidText"]
    return entities.Substitution(
        alignment_id=alignment.id,
        position=mtn["Position"],
        kind=kind,
        **specific_fields,
    )


def substitutions(
    alignment: entities.Alignment, alignment_report: ty.Any
) -> ty.List[entities.Substitution]:
    subs: ty.List[entities.Substitution] = []
    for mtn in alignment_report["Mutations"]:
        subs.append(substitution(alignment, mtn))
    for mtn in alignment_report["FrameShifts"]:
        subs.append(substitution(alignment, mtn))
    return subs


AlignmentEntities = ty.Dict[str, ty.List[ty.NamedTuple]]


def make_entities(
    sequence: entities.Sequence,
    genotype: str,
    subgenotype: ty.Optional[str],
    genes: ty.List[str],
) -> AlignmentEntities:
    "Construct Alignment and Substitution entities from a sequence."
    pname = profile_name(genotype, subgenotype)
    nt_seq = ensure_fasta_formatted(sequence.raw_nt_seq, "Aligned Sequence")
    aln_data: ty.Any = pn.align(nt_seq, pname, genes)
    aln_entities: AlignmentEntities = {"Alignment": [], "Substitution": []}
    for gene in genes:
        reports: ty.Any = aln_data[gene]
        assert len(reports) == 1
        report = reports[0]["Report"]
        aln = alignment(sequence, gene, report)
        subs = substitutions(aln, report)
        aln_entities["Alignment"].append(aln)
        aln_entities["Substitution"].extend(subs)
    return aln_entities
