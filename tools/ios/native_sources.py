"""Enregistre les sources audio dans le projet BeeWare sans toucher à sa signature."""
from hashlib import sha256
from pathlib import Path
import re


def add_native_source(project: Path, name="SpeechController"):
    text = project.read_text()
    if f'/* {name}.m */ = {{isa = PBXFileReference;' in text:
        return
    identifier = lambda name: sha256(name.encode()).hexdigest()[:24].upper()
    header, source, build = [identifier(name) for name in (name + '-header', name + '-source', name + '-build')]
    text = text.replace('/* End PBXBuildFile section */',
        f'\t\t{build} /* {name}.m in Sources */ = {{isa = PBXBuildFile; fileRef = {source} /* {name}.m */; }};\n/* End PBXBuildFile section */', 1)
    references = (f'\t\t{header} /* {name}.h */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = iOSTestbed/{name}.h; sourceTree = SOURCE_ROOT; }};\n'
                  f'\t\t{source} /* {name}.m */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = iOSTestbed/{name}.m; sourceTree = SOURCE_ROOT; }};\n')
    text = text.replace('/* End PBXFileReference section */', references + '/* End PBXFileReference section */', 1)
    text, sources = re.subn(r'(\t{4}[A-F0-9]{24} /\* SceneDelegate.m in Sources \*/,)',
        rf'\1\n\t\t\t\t{build} /* {name}.m in Sources */,', text, count=1)
    text, group = re.subn(r'(\t{4}[A-F0-9]{24} /\* SceneDelegate.m \*/,)',
        rf'\1\n\t\t\t\t{header} /* {name}.h */,\n\t\t\t\t{source} /* {name}.m */,', text, count=1)
    if sources != 1 or group != 1:
        raise ValueError('Structure du projet Xcode inattendue ; aucune écriture')
    project.write_text(text)


def add_speech_sources(project: Path):
    add_native_source(project, "SpeechController")
    add_native_source(project, "SemanticBridge")
