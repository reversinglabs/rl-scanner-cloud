import re
from urllib.parse import quote, unquote

# pkg:npm/%40angular/core@22.1.0 # note the %40 is a encoded @
# pkg:pypi/django@6.0.7?artifact=django-6.0.7-py3-none-any.whl
# --purl my-project/my-package@1.0?build=repro
# pkg:<type>/<namespace>/<name>@version>?qualifiers # a=b&c=d ...
# may have no type : <namespace>/<name>@version>?qualifiers # a=b&c=d ...
# The purl spec: split on the delimiters in the raw string, then percent-decode each component exactly once.


class Purl:
    r"""A Purl supports the normal purl values with:
    pkg:<type>/(<namespace>/)?name@version(\?(qualifiers)+)?
    currently we do not handle the #subpath part of the official Purl schema
    """

    def __init__(self, purl: str) -> None:
        self.purl = purl

        self.pkg_type: str = ""
        self.qualifiers: dict[str, str | None] = {}
        self.namespace: list[str] = []
        self.version: str = ""
        self.name: str = ""
        self._split_purl_in_parts()

    def __repr__(self) -> str:
        return self.to_string()

    def _split_purl_in_parts(self) -> None:
        r = self.purl
        r = self._extract_package_type_01(r)
        r = self._extract_qualifiers_02(r)
        r = self._extract_namespace_03(r)
        self._extract_name_version_04(r)

    def _extract_package_type_01(self, data: str) -> str:
        z: str = data.lower()
        r = re.match(r"^pkg:(\w+)/?", z)
        if r:
            self.pkg_type = unquote(r[1])
            s = f"pkg:{r[1]}/"
            ll = len(s)
            return data[ll:]
        return data

    def _extract_qualifiers_02(self, data: str) -> str:
        # returns the purl minus the qualifiers
        a = data.split("?")
        ll = len(a)
        if ll > 2:
            raise ValueError("Fatal: too many ? in purl string")

        if ll == 1:  # no qualifiers
            return a[0]

        qq = a[1].split("&")
        for item in qq:
            kv = item.split("=", 1)

            k = unquote(kv[0])
            if k in self.qualifiers:
                raise ValueError(f"Fatal: duplicate qualifier keys are not supported: {k}")

            if len(kv) == 2:
                self.qualifiers[k] = unquote(kv[1])
            else:
                self.qualifiers[k] = None

        return a[0]

    def _extract_namespace_03(self, data: str) -> str:
        a = data.split("/")
        ll = len(a)
        if ll == 1:
            return a[0]  # no namespace only name_version

        name_version = a[-1]
        del a[-1]

        for v in a:
            seg = unquote(v)
            if seg in (".", "..") or not seg:
                raise ValueError(f"Fatal: illegal namespace segment in purl: {v!r}")
            self.namespace.append(seg)

        return name_version

    def _extract_name_version_04(self, data: str) -> None:
        if len(data) == 0:
            raise ValueError("at least name must be provided")

        a = data.split("@")  # a split on a empty string returns a [''] so len == 1

        if len(a[0]) == 0:
            raise ValueError("at least name must be provided")

        if len(a) > 2:
            raise ValueError(f"unexpected data after split on '@' {data}")

        if len(a) == 2:
            self.version = unquote(a[1])

        v = a[0]
        seg = unquote(v)
        if seg in (".", "..") or not seg:
            raise ValueError(f"Fatal: illegal name segment in purl: {v!r}")

        self.name = seg

    @classmethod
    def _quote(cls, s: str | None) -> str:
        if s is None:
            return ""
        # return quote(s, safe="", encoding="utf-8", errors="strict").replace(".", "%2E")
        return quote(s, safe="", encoding="utf-8", errors="strict")

    # public
    def to_string(self) -> str:
        r = ""
        if self.pkg_type:
            r = f"pkg:{self.pkg_type}/"

        if len(self.namespace):
            ns = []
            for s1 in self.namespace:
                ns.append(s1)
            r = f"{r}{'/'.join(ns)}/"

        r = f"{r}{self.name}"

        if self.version:
            r = f"{r}@{self.version}"

        if len(self.qualifiers):
            qq: list[str] = []
            for k in sorted(self.qualifiers.keys()):
                t = self.qualifiers[k]
                if t:
                    s2 = f"{k}={t}"
                else:
                    s2 = f"{k}"
                qq.append(s2)

            r = f"{r}?{'&'.join(qq)}"

        return r

    def purl_encoded(self) -> str:
        r = self.get_package_purl()

        if self.version:
            r = f"{r}@{self._quote(self.version)}"

        if len(self.qualifiers):
            qq: list[str] = []
            for k in sorted(self.qualifiers.keys()):
                v = self.qualifiers[k]
                k2 = self._quote(k)
                v2 = self._quote(v)
                if self.qualifiers[k]:
                    s2 = f"{k2}={v2}"
                else:
                    s2 = f"{k2}"
                qq.append(s2)
            r = f"{r}?{'&'.join(qq)}"

        return r

    def has_type(self) -> bool:
        return bool(self.pkg_type)

    def get_package_purl(self) -> str:
        r = ""
        if self.pkg_type:
            r = f"pkg:{self._quote(self.pkg_type)}/"

        if len(self.namespace):
            ns = []
            for s1 in self.namespace:
                ns.append(self._quote(s1))
            r = f"{r}{'/'.join(ns)}/"

        r = f"{r}{self._quote(self.name)}"
        return r  # anything before the @ including pkg:<type/<namespace>/<name>

    def get_version(self) -> str:
        return self.version


class PurlRestrictedRl(Purl):
    def __init__(self, purl: str) -> None:
        super().__init__(purl)

        if "build" in self.qualifiers:
            if self.qualifiers["build"] not in ["version", "repro"]:
                raise ValueError("Fatal: the build qualifier value must be one of 'version' or 'repro'")

        self.build: str = "version"
        if self._has_repro():
            self.build = "repro"
            del self.qualifiers["build"]  # we dont need this anymore

        self._enforce_package_type_rl()
        self._enforce_no_qualifiers_except_build_is()

    def _enforce_no_qualifiers_except_build_is(self) -> None:
        msg = "Fatal: no qualifiers except 'build=[repro|version] are allowed"
        if self.qualifiers:
            keys = list(self.qualifiers.keys())

            if len(keys) > 1:
                raise ValueError(msg)

            if len(keys) == 1 and keys[0] != "build":
                raise ValueError(msg)

    def _enforce_package_type_rl(self) -> None:
        if self.pkg_type:
            if self.pkg_type != "rl":
                raise ValueError("Fatal: for the --purl flag we only accept package type: 'rl'")
        else:
            self.pkg_type = "rl"

    def _has_repro(self) -> bool:
        if "build" in self.qualifiers and self.qualifiers["build"] == "repro":
            return True
        return False

    def has_repro(self) -> bool:
        return self.build == "repro"

    def purl_encoded(self) -> str:
        r = self.get_package_purl()
        if self.version:
            r = f"{r}@{self._quote(self.version)}"
        # no qualifiers
        return r


if __name__ == "__main__":

    def do_it(purl: str) -> None:
        p = Purl(purl)
        print("=====================")
        print(f"purl: {p.purl}")
        print(f"type: {p.pkg_type}")
        print(f"namespace: {p.namespace}")
        print(f"name: {p.name}")
        print(f"version: {p.version}")
        print(f"qual: {p.qualifiers}")
        print(f"purl encoded: {p.purl_encoded()}")
        print(f"purl repr: {p}")
        print("")

    urls = [
        "pkg:jjj/@namespace1/namespace2/name@v1.2.3?bla=klo&artifact=django-6.0.7-py3-none-any.whl&build=repro",
        "@namespace1/namespace2/name@v1.2.3?bla=klo&artifact=django-6.0.7-py3-none-any.whl&build=repro",
        "@namespace1/namespace2/name@v1.2.3",
        "name@v1.2.3",
        "name@",
        "name",
    ]
    for purl in urls:
        do_it(purl)
