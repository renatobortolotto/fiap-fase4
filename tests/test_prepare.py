"""Behavioral checks for real-source preparation; all fixtures are temporary."""
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from voc_olist.prepare import prepare_dataset


REVIEWS = "olist_order_reviews_dataset.csv"
ORDERS = "olist_orders_dataset.csv"
ITEMS = "olist_order_items_dataset.csv"
PRODUCTS = "olist_products_dataset.csv"
R1, R2, O1, O2, P1, P2 = (str(i) * 32 for i in range(1, 7))
REVIEW_FIELDS = [
    "review_id", "order_id", "review_score", "review_comment_title",
    "review_comment_message", "review_creation_date", "review_answer_timestamp",
]


def review(**changes):
    row = dict(zip(REVIEW_FIELDS, [R1, O1, "2", "", "A entrega atrasou.",
                                    "2018-01-20 00:00:00", "2018-01-21 11:00:00"]))
    row.update(changes)
    return row


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw"
        self.raw.mkdir()
        self.out = self.root / "processed"

    def write(self, name, rows, fields=None):
        fields = fields or list(rows[0])
        with (self.raw / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def prepare(self, rows):
        self.write(REVIEWS, rows, REVIEW_FIELDS)
        report = prepare_dataset(self.raw, self.out)
        docs = [json.loads(line) for line in (self.out / "documents.jsonl").read_text(encoding="utf-8").splitlines()]
        return report, docs

    def test_clean_text_title_only_short_comments_and_empty_exclusion(self):
        report, docs = self.prepare([
            review(review_comment_title="  Ótimo&nbsp;&amp;   rápido! ", review_comment_message=" \n\t"),
            review(review_id=R2, review_comment_title="", review_comment_message="<b>Não</b><br> recebi &amp; reclamei."),
            review(review_id="a" * 32, review_comment_message=" \t\n "),
            review(review_id="b" * 32, review_comment_message="ok"),
        ])
        by_id = {d["review_id"]: d for d in docs}
        self.assertEqual(by_id[R1]["text"], "Ótimo & rápido!")
        self.assertEqual(by_id[R2]["text"], "Não recebi & reclamei.")
        self.assertEqual(by_id["b" * 32]["text"], "ok")
        self.assertEqual(report["reviews"]["empty_text_keys_excluded"], 1)
        self.assertEqual(report["reviews"]["title_only_rows"], 1)
        self.assertEqual(report["total_documents"], 3)

    def test_invalid_ids_scores_dates_are_counted(self):
        report, docs = self.prepare([
            review(review_creation_date="not a date", review_answer_timestamp="bad"),
            review(review_id="bad"),
            review(review_id=R2, review_score="6"),
            review(review_id="", review_score="1.5"),
        ])
        self.assertEqual(len(docs), 1)
        self.assertIsNone(docs[0]["review_date"])
        counts = report["reviews"]
        self.assertEqual(counts["input_rows"], 4)
        self.assertEqual(counts["invalid_id_rows"], 2)
        self.assertEqual(counts["invalid_score_rows"], 2)
        self.assertEqual(counts["invalid_rows"], 3)
        self.assertEqual(counts["invalid_review_date_values"], 1)
        self.assertEqual(counts["invalid_answer_timestamp_values"], 1)

    def test_optional_metadata_missing_does_not_require_cloud_or_other_tables(self):
        report, docs = self.prepare([review()])
        self.assertEqual(docs[0]["categories"], [])
        self.assertIsNone(docs[0]["purchase_date"])
        self.assertIsNone(docs[0]["delivered_late"])
        self.assertFalse(report["sources"][ORDERS]["present"])
        self.assertEqual(report["metadata"]["documents_with_order_metadata"], 0)

    def test_multi_item_join_preserves_one_document_and_aggregates_categories(self):
        self.write(PRODUCTS, [
            {"product_id": P1, "product_category_name": "beleza_saude"},
            {"product_id": P2, "product_category_name": "livros"},
        ])
        self.write(ITEMS, [
            {"order_id": O1, "product_id": P1},
            {"order_id": O1, "product_id": P1},
            {"order_id": O1, "product_id": P2},
            {"order_id": O1, "product_id": "f" * 32},
        ])
        self.write(ORDERS, [{
            "order_id": O1, "order_purchase_timestamp": "2018-01-01 13:45:00",
            "order_delivered_customer_date": "2018-01-12 12:00:00",
            "order_estimated_delivery_date": "2018-01-10 00:00:00",
        }])
        report, docs = self.prepare([review()])
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["categories"], ["beleza_saude", "livros"])
        self.assertEqual(docs[0]["purchase_date"], "2018-01-01")
        self.assertIs(docs[0]["delivered_late"], True)
        self.assertEqual(report["sources"][ITEMS]["unique_order_product_pairs"], 3)
        self.assertEqual(report["sources"][ITEMS]["pairs_without_product_metadata"], 1)

    def test_conflict_choice_is_independent_of_csv_order_and_prefers_longer_then_latest(self):
        rows = [
            review(review_comment_message=""),
            review(review_comment_message="Falha A", review_score="1", review_answer_timestamp="2018-02-01"),
            review(review_comment_message="Falha B", review_score="2", review_answer_timestamp="2018-02-02"),
            review(review_comment_message="X", review_score="5", review_answer_timestamp="2019-01-01"),
        ]
        report, docs = self.prepare(rows)
        first_bytes = (self.out / "documents.jsonl").read_bytes()
        report2, docs2 = self.prepare(list(reversed(rows)))
        self.assertEqual(first_bytes, (self.out / "documents.jsonl").read_bytes())
        self.assertEqual(docs, docs2)
        self.assertEqual(docs[0]["message"], "Falha B")
        self.assertEqual(docs[0]["score"], 2)
        self.assertEqual(report["reviews"]["conflicting_rows"], 3)
        self.assertEqual(report2["reviews"]["conflicting_keys"], 1)

    def test_exact_duplicates_and_document_identity(self):
        row = review()
        report, docs = self.prepare([row, row.copy(), review(order_id=O2), review(review_id=R2)])
        self.assertEqual(report["reviews"]["exact_duplicate_rows"], 1)
        self.assertEqual(report["reviews"]["conflicting_rows"], 0)
        self.assertEqual(len(docs), 3)
        self.assertEqual(len({d["doc_id"] for d in docs}), 3)
        expected = hashlib.sha256(f"{R1}:{O1}".encode("ascii")).hexdigest()
        self.assertIn(expected, {d["doc_id"] for d in docs})

    def test_date_only_deadlines_and_unknown_delivery(self):
        fields = ["order_id", "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
        self.write(ORDERS, [
            dict(zip(fields, [O1, "2018-01-01", "2018-01-10 23:59:59", "2018-01-10 00:00:00"])),
            dict(zip(fields, [O2, "bad", "", "2018-01-10"])),
        ])
        report, docs = self.prepare([review(), review(review_id=R2, order_id=O2)])
        by_order = {d["order_id"]: d for d in docs}
        self.assertIs(by_order[O1]["delivered_late"], False)
        self.assertIsNone(by_order[O2]["delivered_late"])
        self.assertIsNone(by_order[O2]["purchase_date"])
        self.assertEqual(report["sources"][ORDERS]["invalid_date_values"], 1)

    def test_multiple_units_of_same_product_are_consolidated_not_labeled_exact_duplicates(self):
        self.write(ITEMS, [
            {"order_id": O1, "product_id": P1, "order_item_id": "1"},
            {"order_id": O1, "product_id": P1, "order_item_id": "2"},
        ])
        self.write(PRODUCTS, [{"product_id": P1, "product_category_name": "livros"}])
        report, docs = self.prepare([review()])
        self.assertEqual(docs[0]["categories"], ["livros"])
        self.assertEqual(report["sources"][ITEMS]["repeated_order_product_rows"], 1)
        self.assertEqual(report["sources"][ITEMS]["exact_duplicate_rows"], 0)

    def test_source_and_documents_hashes_and_saved_report_match(self):
        report, _ = self.prepare([review()])
        self.assertEqual(report["sources"][REVIEWS]["sha256"], hashlib.sha256((self.raw / REVIEWS).read_bytes()).hexdigest())
        self.assertEqual(report["documents_sha256"], hashlib.sha256((self.out / "documents.jsonl").read_bytes()).hexdigest())
        self.assertEqual(report, json.loads((self.out / "preparation_report.json").read_text(encoding="utf-8")))

    def test_missing_required_file_and_missing_schema_fail_clearly(self):
        with self.assertRaisesRegex(FileNotFoundError, "Arquivo obrigatório"):
            prepare_dataset(self.raw, self.out)
        self.write(REVIEWS, [{"review_id": R1}], ["review_id"])
        with self.assertRaisesRegex(ValueError, "colunas obrigatórias ausentes"):
            prepare_dataset(self.raw, self.out)
        self.assertFalse((self.out / "documents.jsonl").exists())

    def test_present_optional_file_requires_valid_schema(self):
        self.write(REVIEWS, [review()], REVIEW_FIELDS)
        self.write(ITEMS, [{"order_id": O1}], ["order_id"])
        with self.assertRaisesRegex(ValueError, "product_id"):
            prepare_dataset(self.raw, self.out)

    def test_no_valid_customer_text_fails_without_inventing_a_corpus(self):
        self.write(REVIEWS, [review(review_comment_message="")], REVIEW_FIELDS)
        with self.assertRaisesRegex(ValueError, "Nenhuma avaliação válida com texto"):
            prepare_dataset(self.raw, self.out)
        self.assertFalse((self.out / "documents.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
