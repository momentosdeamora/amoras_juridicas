from pathlib import Path
import unittest
try:import yaml
except ImportError:yaml=None

@unittest.skipUnless(yaml,'Validação YAML requer o grupo dev do Poetry')
class ContainerConfigTests(unittest.TestCase):
    def setUp(self):self.config=yaml.safe_load(Path('compose.yaml').read_text())
    def test_inference_network_has_no_external_connectivity(self):
        self.assertTrue(self.config['networks']['private']['internal'])
        for name in ('app','ollama'):self.assertEqual(self.config['services'][name]['networks'],['private'])
    def test_ollama_not_exposed_and_cloud_disabled(self):
        model=self.config['services']['ollama'];self.assertNotIn('ports',model)
        self.assertEqual(model['environment']['OLLAMA_NO_CLOUD'],'1')
    def test_nonroot_readonly_no_privileges(self):
        for name in ('app','ollama'):
            service=self.config['services'][name]
            self.assertNotEqual(service['user'].split(':')[0],'0');self.assertTrue(service['read_only'])
            self.assertIn('ALL',service['cap_drop']);self.assertIn('no-new-privileges:true',service['security_opt'])
    def test_app_loopback_and_auth_required(self):
        app=self.config['services']['app']
        self.assertTrue(app['ports'][0].startswith('127.0.0.1:'))
        self.assertEqual(app['environment']['FAROL_REQUIRE_AUTH'],'1')
        self.assertIn('farol_access_token',app['secrets'])
    def test_download_is_opt_in_and_runtime_has_no_docker_socket(self):
        self.assertEqual(self.config['services']['model-download']['profiles'],['setup'])
        for service in self.config['services'].values():
            self.assertNotIn('privileged',service)
            self.assertNotIn('docker.sock',str(service.get('volumes',[])))
    def test_secrets_and_runtime_excluded_from_build(self):
        excluded=Path('.dockerignore').read_text().splitlines()
        for path in ('.secrets','.runtime','.tools','.venv','data'):self.assertIn(path,excluded)

if __name__=='__main__':unittest.main()
