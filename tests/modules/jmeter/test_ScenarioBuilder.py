from . import MockJMeterExecutor
from bzt.modules.jmeter import JMeterScenarioBuilder
from tests import BZTestCase, RESOURCES_DIR
from tempfile import NamedTemporaryFile
from bzt.six import etree


class TestScenarioBuilder(BZTestCase):
    def setUp(self):
        super(TestScenarioBuilder, self).setUp()
        executor = MockJMeterExecutor({"scenario": "SB"})
        executor.engine.config.merge({"scenarios": {"SB": {}}})

        self.obj = JMeterScenarioBuilder(executor)

        self.jmx_fd = NamedTemporaryFile()
        self.jmx = self.jmx_fd.name

    def tearDown(self):
        self.jmx_fd.close()
        super(TestScenarioBuilder, self).tearDown()

    def configure(self, scenario, version="3.3"):
        self.obj.scenario.data.merge(scenario)
        self.obj.executor.settings["version"] = version

    @staticmethod
    def get_plugin_json_extractor_config(xml_tree):
        cfg = {}
        block_name = "com.atlantbh.jmeter.plugins.jsonutils.jsonpathextractor.JSONPathExtractor"
        blocks = xml_tree.findall(".//%s" % block_name)
        for block in blocks:
            varname = block.find(".//stringProp[@name='VAR']")
            jsonpath = block.find(".//stringProp[@name='JSONPATH']")
            default = block.find(".//stringProp[@name='DEFAULT']")
            subject = block.find(".//stringProp[@name='SUBJECT']")
            from_variable = block.find(".//stringProp[@name='VARIABLE']")
            varname = varname.text
            jsonpath = jsonpath.text
            if default is not None:
                default = default.text
            if (subject is not None) and subject.text == "VAR" and (from_variable is not None):
                from_variable = from_variable.text
            else:
                from_variable = None
            cfg[varname] = {"jsonpath": jsonpath, "default": default, "from_variable": from_variable}
        return cfg

    @staticmethod
    def get_internal_json_extractor_config(xml_tree):
        cfg = {}
        blocks = xml_tree.findall(".//JSONPostProcessor")
        for block in blocks:
            varname = block.find(".//stringProp[@name='VAR']")
            jsonpath = block.find(".//stringProp[@name='JSONPostProcessor.jsonPathExprs']")
            default = block.find(".//stringProp[@name='JSONPostProcessor.defaultValues']")
            match_num = block.find(".//stringProp[@name='JSONPostProcessor.match_numbers']")
            scope = block.find(".//stringProp[@name='Sample.scope']")
            from_variable = block.find(".//stringProp[@name='Scope.variable']")
            concat = block.find(".//booleanProp[@name='JSONPostProcessor.compute_concat']")
            varname = varname.text
            jsonpath = jsonpath.text
            if default is not None:
                default = default.text
            if (scope is not None) and scope.text == "variable" and (from_variable is not None):
                scope = scope.text
                from_variable = from_variable.text
            else:
                from_variable = None

            cfg[varname] = {"jsonpath": jsonpath, "default": default, "scope": scope,
                            "from_variable": from_variable, "match_num": match_num, "concat": concat}

        return cfg

    def test_plugin_config_reader(self):
        xml_tree = etree.fromstring(open(RESOURCES_DIR + "jmeter/jmx/json_extractors.jmx", "rb").read())
        target = {}
        self.assertEqual(target, self.get_plugin_json_extractor_config(xml_tree))

    def test_old_jmeter(self):
        """ versions before 3.0 must use JSON plugin for extracting purposes """
        self.configure(scenario={"requests": [{
                "url": "http://blazedemo.com",
                "extract-jsonpath": {
                    "IP": "$.net[0].ip",
                    "URL": {
                        "jsonpath": "$.net[1].url",
                        "default": "def",
                        "from-variable": "Jm_VaR"}}}]},
            version="2.13")
        self.obj.save(self.jmx)
        xml_tree = etree.fromstring(open(self.jmx, "rb").read())
        cfg = self.get_plugin_json_extractor_config(xml_tree)
        self.assertEqual(2, len(cfg))
        target = {
            "IP": {"jsonpath": "$.net[0].ip", "default": "NOT_FOUND", "from_variable": None},
            "URL": {"jsonpath": "$.net[1].url", "default": "def", "from_variable": "Jm_VaR"}}
        self.assertEqual(target, cfg)

    def test_new_extractor(self):
        """ versions after 3.0 use integrated JSON extractor """
        self.configure(scenario={"requests": [{
            "url": "http://blazedemo.com",
            "extract-jsonpath": {"IP": "$.net[0].ip"}}]},
            version="3.3")
        self.obj.save(self.jmx)
        xml_tree = etree.fromstring(open(self.jmx, "rb").read())
        cfg = self.get_internal_json_extractor_config(xml_tree)
        self.assertEqual(1, len(cfg))
        target = {"IP": {"jsonpath": "$.net[0].ip", "default": "NOT_FOUND"}}
        self.assertEqual(target, cfg)

