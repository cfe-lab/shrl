import textwrap
import unittest
import uuid

from shrl import metadata


def parse_config_str(src):
    parser = metadata.get_parser()
    parser.read_string(src)
    return parser


class TestParseCollaborator(unittest.TestCase):
    def test_load_collaborator(self):
        src = textwrap.dedent(
            """\
            [collaborator]
            id=af8e1177-a043-4d10-963d-5eb76af13566
            name=asdf
            """
        )
        parsed = parse_config_str(src)
        extracted = metadata.collaborators(parsed)
        expected_collab = metadata.Collaborator(
            id=uuid.UUID("af8e1177-a043-4d10-963d-5eb76af13566"), name="asdf"
        )
        self.assertEqual(extracted, [expected_collab])

    def test_load_multiple_collaborators(self):
        src = textwrap.dedent(
            """\
            [collaborator.1]
            id=af8e1177-a043-4d10-963d-5eb76af13566
            name=asdf

            [collaborator.2]
            id=af8e1177-a043-4d10-963d-5eb76af13567
            name = jkl
            """
        )
        parsed = parse_config_str(src)
        extracted = metadata.collaborators(parsed)
        expected = [
            metadata.Collaborator(
                id=uuid.UUID("af8e1177-a043-4d10-963d-5eb76af13566"),
                name="asdf",
            ),
            metadata.Collaborator(
                id=uuid.UUID("af8e1177-a043-4d10-963d-5eb76af13567"),
                name="jkl",
            ),
        ]
        self.assertEqual(extracted, expected)

    def test_missing_collaborator_raises_error(self):
        src = ""
        parsed = parse_config_str(src)
        with self.assertRaises(metadata.MetadataError):
            metadata.collaborators(parsed)
