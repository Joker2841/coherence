from coherence.trust import TrustLedger


def test_everyone_starts_at_one():
    L = TrustLedger()
    for s in ["Phil", "Stu", "Mr. Chow"]:
        L.register(s)
    assert all(v == 1.0 for v in L.all_trust().values())


def test_loss_drops_winner_holds():
    L = TrustLedger()
    for s in ["Phil", "Stu", "Alan"]:
        L.register(s)
    L.record_resolution(winner_source="Stu", loser_source="Phil")
    assert L.trust("Phil") == 0.5      # (0+1)/(0+1+1)
    assert L.trust("Stu") == 1.0       # winning never drops trust
    assert L.trust("Alan") == 1.0      # uninvolved unchanged


def test_losses_compound():
    L = TrustLedger()
    L.register("Phil")
    L.record_resolution("Stu", "Phil")
    L.record_resolution("Stu", "Phil")
    assert L.trust("Phil") == 0.33     # (0+1)/(0+2+1)


def test_unknown_source_is_trusted():
    assert TrustLedger().trust(None) == 1.0