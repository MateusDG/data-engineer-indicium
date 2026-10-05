"""Regression checks for accidental disclosure through the deliverable archive."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_delivery import package_project


class DeliveryTests(unittest.TestCase):
    def test_includes_code_and_public_evidence_without_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["README.md", "dags/pipeline.py", "infra/main.tf", "infra/.terraform.lock.hcl",
                         "meltano/meltano.yml", "sql/bootstrap.sql", "evidence/counts.json"]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("public")
            destination = root / "delivery/project.zip"
            names = package_project(root, destination)
            self.assertIn("dags/pipeline.py", names)
            self.assertIn("infra/.terraform.lock.hcl", names)
            self.assertIn("data/input/.gitkeep", names)
            with zipfile.ZipFile(destination) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(set(archive.namelist()), set(names))

    def test_dashboard_assets_and_locks_are_included_without_node_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            public = ['commercial/static/app.js','commercial/static/style.css','commercial/static/mark.svg',
                      'commercial/requirements.lock','commercial/requirements.in','commercial/package-lock.json',
                      'commercial/static/vendor/echarts.min.js','infra/commercial/main.tf']
            for name in public+['commercial/node_modules/echarts/package.json']:
                path = root/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('public')
            names = package_project(root,root/'delivery/project.zip')
            self.assertTrue(set(public).issubset(names))
            self.assertNotIn('commercial/node_modules/echarts/package.json',names)

    def test_excludes_nested_secrets_state_and_source_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blocked = ["config/credentials.json", "config/passwords.json", "config/secrets.json",
                       "meltano/.env", "meltano/.env.local", "infra/debug.tfstate.json",
                       "infra/debug.tfplan.json", "infra/.terraform/cache.json",
                       "evidence/private/customers.json", "meltano/.meltano/state.json",
                       "config/source.csv", "config/source.zip", "data/input/source.zip"]
            for name in blocked:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("SECRET_SENTINEL")
            destination = root / "delivery/project.zip"
            names = package_project(root, destination)
            self.assertEqual(names, ["data/input/.gitkeep"])
            with zipfile.ZipFile(destination) as archive:
                self.assertNotIn(b"SECRET_SENTINEL", b"".join(archive.read(n) for n in names))


if __name__ == "__main__":
    unittest.main()
