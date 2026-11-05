"""Responsible for the safety checks in code: filtering prompt injection and checking answers against their sources."""
import re

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts)",
    r"disregard (all |any |the )?(previous|prior|above|earlier|your) (instructions|rules)",
    r"(reveal|show|print|repeat) (me )?(your|the) (system )?(prompt|instructions)",
    r"act as (an? )?(unrestricted|different|new)",
    r"developer mode|jailbreak",
    r"new instructions:",
    r"</?(system|assistant)>",
]
SOURCE_TAG = re.compile(r"\[S(\d+)\]")
MIN_WORD_OVERLAP = 0.5


# True when the text looks like an attempt to give the model new instructions.
def is_injection(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in INJECTION_PATTERNS)


# Returns "prompt_injection" when the agent's question is an attack, otherwise None.
def check_input(question: str) -> str | None:
    if is_injection(question):
        return "prompt_injection"
    return None


# Drops retrieved clauses that contain injection text, so they never reach the model.
def filter_chunks(chunks: list[dict]) -> list[dict]:
    return [chunk for chunk in chunks if not is_injection(chunk["text"])]


# Splits an answer into sentences. A new line also ends a sentence, so every bullet is checked on its own.
def split_sentences(text: str) -> list[str]:
    return [sentence for sentence in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if sentence]


# Returns the numbers in a text without commas, so "5,00,000" and "500000" compare equal.
def numbers_in(text: str) -> list[str]:
    return [number.replace(",", "") for number in re.findall(r"\d[\d,]*", text)]


# Returns why an answer is not backed by its sources, or None when every sentence is.
def check_grounding(answer: str, chunks: list[dict]) -> str | None:
    sentences = split_sentences(answer)
    if not sentences:
        return "empty_answer"
    for sentence in sentences:
        tags = [int(number) for number in SOURCE_TAG.findall(sentence)]
        if not tags:
            return "uncited_claim"
        if any(number < 1 or number > len(chunks) for number in tags):
            return "fake_citation"
        source_text = " ".join(chunks[number - 1]["text"] for number in tags).lower()
        claim = SOURCE_TAG.sub("", sentence).lower()
        # Every number in the claim must appear as a number in the cited source.
        source_numbers = set(numbers_in(source_text))
        if any(number not in source_numbers for number in numbers_in(claim)):
            return "unsupported_claim"
        # At least half of the claim's longer words must appear in the cited source.
        claim_words = re.findall(r"[a-z]{4,}", claim)
        found = sum(1 for word in claim_words if word in source_text)
        if claim_words and found / len(claim_words) < MIN_WORD_OVERLAP:
            return "unsupported_claim"
    return None


# Returns the citations (source, clause, version) for every valid [S#] tag in the answer, in order, without repeats.
def citations_for(answer: str, chunks: list[dict]) -> list[dict]:
    numbers = []
    for number in (int(n) for n in SOURCE_TAG.findall(answer)):
        if 1 <= number <= len(chunks) and number not in numbers:
            numbers.append(number)
    citations = []
    for number in numbers:
        chunk = chunks[number - 1]
        citations.append(
            {"source_id": chunk["source_id"], "clause_id": chunk["clause_id"], "version": chunk["version"]}
        )
    return citations


# Removes the [S#] tags so the answer reads cleanly.
def strip_tags(answer: str) -> str:
    return SOURCE_TAG.sub("", answer).replace(" .", ".").strip()
