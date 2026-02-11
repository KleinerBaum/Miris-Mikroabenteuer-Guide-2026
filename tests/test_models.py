from mikroabenteuer.models import Adventure, SafetyProfile


def test_adventure_model() -> None:
    safety = SafetyProfile(
        risks=["Test Risiko"],
        prevention=["Test Prävention"],
    )

    adventure = Adventure(
        id="test",
        title="Test Abenteuer",
        location="Test Ort",
        duration="10 Minuten",
        intro_quote="Test Quote",
        description="Beschreibung",
        preparation=["Vorbereitung"],
        steps=["Schritt 1"],
        child_benefit="Gut für Entwicklung",
        carla_tip="Tipp",
        safety=safety,
    )

    assert adventure.title == "Test Abenteuer"
