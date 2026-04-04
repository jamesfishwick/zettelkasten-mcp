"""Seed data for eval tests -- builds a realistic slipbox state."""
from slipbox_mcp.models.schema import LinkType, NoteType


def populate_slipbox(zettel_service) -> dict[str, str]:
    """Build a 15-note slipbox with links and return ID reference dict.

    Returns dict mapping descriptive keys to note IDs, e.g.:
        {"hub_philosophy": "20260403...", "permanent_stoic_letters": "20260403...", ...}
    """
    # -- Hub (1) --
    hub = zettel_service.create_note(
        title="Philosophy",
        content=(
            "Philosophy is the practice of examining fundamental questions about "
            "existence, knowledge, values, and reason. It is not merely academic "
            "but a way of living deliberately."
        ),
        note_type=NoteType.HUB,
        tags=["philosophy"],
    )

    # -- Structure (2) --
    stoicism = zettel_service.create_note(
        title="Stoicism Overview",
        content=(
            "Stoicism is a Hellenistic philosophy founded in Athens by Zeno of "
            "Citium. Key concepts include the dichotomy of control, virtue as the "
            "sole good, and living in accordance with nature. This note organizes "
            "the main stoic ideas explored in this slipbox."
        ),
        note_type=NoteType.STRUCTURE,
        tags=["stoicism", "philosophy"],
    )

    epistemology = zettel_service.create_note(
        title="Epistemology Overview",
        content=(
            "Epistemology is the branch of philosophy concerned with the nature, "
            "sources, and limits of knowledge. This structure note organizes notes "
            "on competing epistemological traditions."
        ),
        note_type=NoteType.STRUCTURE,
        tags=["epistemology", "philosophy"],
    )

    # -- Permanent (6) --
    seneca = zettel_service.create_note(
        title="Seneca's Letters on Anger",
        content=(
            "In De Ira, Seneca argues that anger is a temporary madness and can be "
            "overcome through rational self-examination. He prescribes a nightly "
            "review of the day's events as a method for catching and defusing anger "
            "before it takes hold."
        ),
        note_type=NoteType.PERMANENT,
        tags=["stoicism", "seneca", "emotions"],
    )

    marcus = zettel_service.create_note(
        title="Marcus Aurelius on Impermanence",
        content=(
            "Marcus Aurelius repeatedly returns to the theme of impermanence in "
            "the Meditations. Everything is in flux; what seems solid will dissolve. "
            "This awareness should free us from attachment and bring equanimity."
        ),
        note_type=NoteType.PERMANENT,
        tags=["stoicism", "marcus-aurelius", "meditation"],
    )

    journaling = zettel_service.create_note(
        title="Stoic Journaling Practice",
        content=(
            "The Stoics practiced daily reflection through journaling. Marcus "
            "Aurelius wrote the Meditations as a personal journal. Seneca reviewed "
            "his day each evening. Modern practitioners adapt these techniques "
            "into structured morning and evening routines."
        ),
        note_type=NoteType.PERMANENT,
        tags=["stoicism", "journaling", "practice"],
    )

    plato = zettel_service.create_note(
        title="Plato's Theory of Forms",
        content=(
            "Plato posits a realm of abstract, perfect Forms (Ideas) that exist "
            "independently of the physical world. Material objects are imperfect "
            "copies of these Forms. True knowledge is knowledge of the Forms, "
            "accessible only through reason, not the senses."
        ),
        note_type=NoteType.PERMANENT,
        tags=["epistemology", "plato", "metaphysics"],
    )

    empiricism = zettel_service.create_note(
        title="Empiricism vs Rationalism",
        content=(
            "Empiricists (Locke, Hume) hold that knowledge derives from sensory "
            "experience. Rationalists (Descartes, Leibniz) argue that reason alone "
            "can yield knowledge independent of experience. This debate shapes "
            "modern philosophy of science and epistemology."
        ),
        note_type=NoteType.PERMANENT,
        tags=["epistemology", "philosophy-of-science"],
    )

    cbt = zettel_service.create_note(
        title="Cognitive Behavioral Therapy Origins",
        content=(
            "CBT was developed by Aaron Beck in the 1960s, but its intellectual "
            "roots trace back to Stoic philosophy. The core CBT insight -- that "
            "our beliefs about events, not the events themselves, cause emotional "
            "distress -- closely mirrors Epictetus's Enchiridion."
        ),
        note_type=NoteType.PERMANENT,
        tags=["psychology", "cbt", "stoicism"],
    )

    # -- Literature (2) --
    meditations = zettel_service.create_note(
        title="Notes on Meditations",
        content=(
            "Reading notes from Marcus Aurelius's Meditations. Key themes: "
            "impermanence, duty, the inner citadel, cosmopolitanism. The text is "
            "structured as a personal journal rather than a treatise, giving it "
            "an intimate, unpolished quality."
        ),
        note_type=NoteType.LITERATURE,
        tags=["stoicism", "marcus-aurelius"],
        references=["Aurelius, M. Meditations. Penguin Classics."],
    )

    smart_notes = zettel_service.create_note(
        title="Notes on How to Take Smart Notes",
        content=(
            "Ahrens argues that writing is not the output of thinking but the "
            "medium in which thinking happens. The slip-box method externalizes "
            "ideas so they can be connected, reordered, and discovered over time."
        ),
        note_type=NoteType.LITERATURE,
        tags=["zettelkasten", "methodology"],
        references=["Ahrens, S. (2017). How to Take Smart Notes."],
    )

    # -- Fleeting (2) --
    cbt_question = zettel_service.create_note(
        title="Could CBT be Stoic philosophy repackaged?",
        content=(
            "Struck by the parallels between CBT techniques and Stoic exercises. "
            "Is CBT essentially Stoicism with a clinical veneer? Need to trace "
            "the historical influence more carefully."
        ),
        note_type=NoteType.FLEETING,
        tags=["cbt", "stoicism", "question"],
    )

    skepticism = zettel_service.create_note(
        title="Read more about Pyrrhonian skepticism",
        content=(
            "Pyrrhonian skepticism seems like an important counterpoint to both "
            "rationalism and empiricism. Add Sextus Empiricus to reading list."
        ),
        note_type=NoteType.FLEETING,
        tags=["epistemology", "reading-list"],
    )

    # -- Orphan (1) --
    pasta = zettel_service.create_note(
        title="Best Pasta Recipes",
        content=(
            "Cacio e pepe: pecorino, black pepper, pasta water. The key is "
            "emulsifying the cheese with starchy water off heat. Carbonara: "
            "guanciale, egg yolks, pecorino, black pepper -- never cream."
        ),
        note_type=NoteType.PERMANENT,
        tags=["cooking", "recipes"],
    )

    # -- Links --
    # Hub -> Structure
    zettel_service.create_link(hub.id, stoicism.id, LinkType.REFERENCE)
    zettel_service.create_link(hub.id, epistemology.id, LinkType.REFERENCE)

    # Structure -> Permanent (stoicism branch)
    zettel_service.create_link(stoicism.id, seneca.id, LinkType.REFERENCE)
    zettel_service.create_link(stoicism.id, marcus.id, LinkType.REFERENCE)
    zettel_service.create_link(stoicism.id, journaling.id, LinkType.REFERENCE)

    # Permanent <-> Permanent
    zettel_service.create_link(seneca.id, marcus.id, LinkType.EXTENDS)
    zettel_service.create_link(cbt.id, seneca.id, LinkType.SUPPORTS)

    # Structure -> Permanent (epistemology branch)
    zettel_service.create_link(epistemology.id, plato.id, LinkType.REFERENCE)
    zettel_service.create_link(epistemology.id, empiricism.id, LinkType.REFERENCE)

    # Permanent <-> Permanent (epistemology)
    zettel_service.create_link(plato.id, empiricism.id, LinkType.CONTRADICTS)

    # Literature -> Permanent
    zettel_service.create_link(meditations.id, marcus.id, LinkType.SUPPORTS)

    # Fleeting -> Permanent
    zettel_service.create_link(cbt_question.id, cbt.id, LinkType.RELATED)

    return {
        "hub_philosophy": hub.id,
        "structure_stoicism": stoicism.id,
        "structure_epistemology": epistemology.id,
        "permanent_seneca": seneca.id,
        "permanent_marcus": marcus.id,
        "permanent_journaling": journaling.id,
        "permanent_plato": plato.id,
        "permanent_empiricism": empiricism.id,
        "permanent_cbt": cbt.id,
        "literature_meditations": meditations.id,
        "literature_smart_notes": smart_notes.id,
        "fleeting_cbt_question": cbt_question.id,
        "fleeting_skepticism": skepticism.id,
        "orphan_pasta": pasta.id,
    }
