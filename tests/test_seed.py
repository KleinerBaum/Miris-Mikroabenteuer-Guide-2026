# tests/test_seed.py
from mikroabenteuer.data_seed import seed_adventures


def test_seed_unique_slugs_and_validate():
    adventures = seed_adventures()
    assert len(adventures) >= 30

    slugs = [a.slug for a in adventures]
    assert len(slugs) == len(set(slugs))

    # validate() is already called inside seed_adventures(), but we assert anyway
    for a in adventures:
        a.validate()
