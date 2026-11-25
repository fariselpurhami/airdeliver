"""Guard authored application copy without renaming technical identifiers."""
import io
from pathlib import Path
import re
import tokenize


def test_application_string_literals_keep_lowercase_brand():
    violations = []
    for path in (Path(__file__).parents[1] / 'app').rglob('*.py'):
        for token in tokenize.generate_tokens(io.StringIO(path.read_text()).readline):
            if token.type != tokenize.STRING:
                continue
            # These are legacy input spellings consumed by the sanitizer, not output.
            if token.string in ('"AirDeliver"', '"Airdeliver"'):
                continue
            if re.search(r'\b(?:AirDeliver|Airdeliver|AIRDELIVER)\b', token.string):
                violations.append(f'{path.relative_to(path.parents[3])}:{token.start[0]}')
    assert not violations, violations
