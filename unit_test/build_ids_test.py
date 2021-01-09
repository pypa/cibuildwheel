import toml
from toml.encoder import TomlEncoder

from cibuildwheel.util import resources_dir


class InlineArrayDictEncoder(TomlEncoder):
    def dump_sections(self, o: dict, sup: str):
        if all(isinstance(a, list) for a in o.values()):
            val = ""
            for k, v in o.items():
                inner = ",\n  ".join(self.dump_inline_table(d_i).strip() for d_i in v)
                val += f"{k} = [\n  {inner},\n]\n"
            return val, self._dict()
        else:
            return super().dump_sections(o, sup)


def test_compare_configs():
    with open(resources_dir / "build-platforms.toml") as f:
        txt = f.read()

    dict_txt = toml.loads(txt)

    new_txt = toml.dumps(dict_txt, encoder=InlineArrayDictEncoder())
    print(new_txt)

    assert new_txt == txt
