from dataclasses import dataclass, field


@dataclass
class Protein:
    identifier: str
    length: int
    accession: str | None = None
    crc64: str | None = None
    reviewed: bool = False
    complete: bool = field(default=True, init=False)
    taxon_id: int | None = field(default=None, init=False)
    lineage: list = field(default_factory=list, init=False)
    species: str | None = field(default=None, init=False)
    ref_proteome: bool = field(default=False, init=False)
    hits: list = field(default_factory=list, init=False)

    def clean(self):
        self.species = self.species.rstrip(".")


@dataclass
class Entry:
    accession: str
    name: str
    description: str
    type: str
    num_alphafold: int = field(default=0, init=False)
    dom_score: float = field(default=0, init=False)
    glo_score: float = field(default=0, init=False)
    dists: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.dists = {
            "glo_bact": [0] * 100,
            "glo_euk": [0] * 100,
            "glo_arch": [0] * 100,
            "glo_others": [0] * 100,
            "dom_bact": [0] * 100,
            "dom_euk": [0] * 100,
            "dom_arch": [0] * 100,
            "dom_others": [0] * 100,
            "glo_bact_nofrags": [0] * 100,
            "glo_euk_nofrags": [0] * 100,
            "glo_arch_nofrags": [0] * 100,
            "glo_others_nofrags": [0] * 100,
            "dom_bact_nofrags": [0] * 100,
            "dom_euk_nofrags": [0] * 100,
            "dom_arch_nofrags": [0] * 100,
            "dom_others_nofrags": [0] * 100,
        }

    @classmethod
    def fromdict(cls, obj: dict):
        entry = cls(accession=obj["id"],
                    name=obj["name"],
                    description=obj["description"],
                    type=obj["type"])
        return entry
