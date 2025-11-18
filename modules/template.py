from core.module import BaseModule
from core.output import print_json


class TemplateModule(BaseModule):
    name = "template"
    description = "Example module template"
    author = "DarkReconX"

    def run(self, text: str = "hello"):
        data = {"result": text}
        print_json(data)
        return data
