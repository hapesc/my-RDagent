from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class HypothesisRecord:
    text: str
    score: float
    timestamp: float
    branch_id: str


class TFIDFVectorizer:
    def __init__(self) -> None:
        self._idf = {}  # type: Dict[str, float]
        self._vocab = set()  # type: Set[str]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return text.lower().split()

    def fit_transform(self, documents: List[str]) -> List[Dict[str, float]]:
        n_docs = len(documents)
        if n_docs == 0:
            return []

        tokenized = [self._tokenize(doc) for doc in documents]

        df = {}  # type: Dict[str, int]
        self._vocab = set()
        for tokens in tokenized:
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1
                self._vocab.add(token)

        self._idf = {}
        for term, count in df.items():
            self._idf[term] = math.log((1.0 + float(n_docs)) / (1.0 + float(count))) + 1.0

        vectors = []  # type: List[Dict[str, float]]
        for tokens in tokenized:
            if not tokens:
                vectors.append({})
                continue

            tf = {}  # type: Dict[str, float]
            token_count = float(len(tokens))
            for token in tokens:
                tf[token] = tf.get(token, 0.0) + 1.0

            tfidf = {}  # type: Dict[str, float]
            for token, count in tf.items():
                tf_value = count / token_count
                weight = tf_value * self._idf.get(token, 0.0)
                if weight > 0.0:
                    tfidf[token] = weight

            vectors.append(tfidf)

        return vectors

    def transform(self, document: str) -> Dict[str, float]:
        tokens = self._tokenize(document)
        if not tokens:
            return {}

        tf = {}  # type: Dict[str, float]
        token_count = float(len(tokens))
        for token in tokens:
            if token in self._vocab:
                tf[token] = tf.get(token, 0.0) + 1.0

        if not tf:
            return {}

        tfidf = {}  # type: Dict[str, float]
        for token, count in tf.items():
            tf_value = count / token_count
            weight = tf_value * self._idf.get(token, 0.0)
            if weight > 0.0:
                tfidf[token] = weight

        return tfidf


def cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0

    dot = 0.0
    for key, value in vec_a.items():
        dot += value * vec_b.get(key, 0.0)

    if dot == 0.0:
        return 0.0

    mag_a = math.sqrt(sum(value * value for value in vec_a.values()))
    mag_b = math.sqrt(sum(value * value for value in vec_b.values()))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0

    similarity = dot / (mag_a * mag_b)
    if similarity < 0.0:
        return 0.0
    if similarity > 1.0:
        return 1.0
    return similarity


def score_delta(score_a: float, score_b: float) -> float:
    similarity = 1.0 - abs(score_a - score_b)
    if similarity < 0.0:
        return 0.0
    if similarity > 1.0:
        return 1.0
    return similarity


def temporal_decay(timestamp_a: float, timestamp_b: float, half_life: float = 3600.0) -> float:
    dt = abs(timestamp_a - timestamp_b)
    if dt == 0.0:
        return 1.0
    if half_life <= 0.0:
        return 0.0
    decay = math.pow(0.5, dt / half_life)
    if decay < 0.0:
        return 0.0
    if decay > 1.0:
        return 1.0
    return decay


class InteractionKernel:
    def __init__(self, alpha: float = 0.4, beta: float = 0.3, gamma: float = 0.3) -> None:
        self._alpha = alpha
        self._beta = beta
        self._gamma = gamma
        self._vectorizer = TFIDFVectorizer()

    def compute(self, h_a: HypothesisRecord, h_b: HypothesisRecord) -> float:
        vectors = self._vectorizer.fit_transform([h_a.text, h_b.text])
        cosine = cosine_similarity(vectors[0], vectors[1])
        delta = score_delta(h_a.score, h_b.score)
        decay = temporal_decay(h_a.timestamp, h_b.timestamp)

        result = self._alpha * cosine + self._beta * delta + self._gamma * decay
        if result < 0.0:
            return 0.0
        if result > 1.0:
            return 1.0
        return result
