import copy
import unittest

from zis.contracts import ContractError, validate
from zis.identity import enforce_identity_boundary
from tests.helpers import capability, evidence, idea, observation, specialist


class ContractTests(unittest.TestCase):
    def test_all_valid_examples(self):
        for name, record in (("evidence", evidence()), ("observation", observation()), ("specialist", specialist()), ("capability", capability()), ("idea", idea())):
            with self.subTest(name=name):
                validate(name, record)

    def test_all_invalid_examples(self):
        for name, record in (("evidence", evidence()), ("observation", observation()), ("specialist", specialist()), ("capability", capability()), ("idea", idea())):
            with self.subTest(name=name):
                invalid = copy.deepcopy(record)
                invalid.pop(next(iter(invalid)))
                with self.assertRaises(ContractError):
                    validate(name, invalid)

    def test_invalid_confidence_and_timestamp(self):
        record = evidence()
        record["confidence"] = "87_percent"
        record["observed_at"] = "yesterday"
        with self.assertRaises(ContractError):
            validate("evidence", record)

    def test_unknown_fields_rejected(self):
        record = evidence()
        record["email"] = "private@example.test"
        with self.assertRaises(ContractError):
            validate("evidence", record)

    def test_identity_fields_rejected_recursively(self):
        with self.assertRaisesRegex(ValueError, "real_name"):
            enforce_identity_boundary({"provenance": {"real_name": "Private Person"}})

    def test_persistent_capability_cannot_be_approved_without_approval(self):
        record = capability()
        record.update({"proposed_solution_level": "small_tool", "status": "implemented", "approval_status": "pending"})
        with self.assertRaises(ContractError):
            validate("capability", record)


if __name__ == "__main__":
    unittest.main()

