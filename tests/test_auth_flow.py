import os, sys, types, importlib
import pytest

# Force SQLAlchemy to use in-memory SQLite to avoid Postgres driver
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

# --- Patch heavy deps (numpy, pandas, nltk, regex) with dummy modules before they are imported ---
for mod_name in ['numpy', 'pandas', 'nltk', 'regex', 'regex._regex', 'pytz', 'dateutil']:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

# --- Stub tiktoken early to avoid binary dependency and circular import ---
if 'tiktoken' not in sys.modules:
    tiktoken_stub = types.ModuleType('tiktoken')

    class _DummyEncoding:
        def encode(self, text):
            return []

        def decode(self, tokens):
            return ''

    # core submodule
    core_mod = types.ModuleType('tiktoken.core')
    core_mod.Encoding = _DummyEncoding

    # Provide get_encoding and encoding_for_model helpers
    def _dummy_get_encoding(name='cl100k_base'):
        return _DummyEncoding()

    tiktoken_stub.get_encoding = _dummy_get_encoding
    tiktoken_stub.encoding_for_model = lambda model: _DummyEncoding()

    # add core module and _tiktoken stub
    _tiktoken_mod = types.ModuleType('tiktoken._tiktoken')

    sys.modules['tiktoken'] = tiktoken_stub
    sys.modules['tiktoken.core'] = core_mod
    sys.modules['tiktoken._tiktoken'] = _tiktoken_mod

    # Attach submodules to parent
    tiktoken_stub.core = core_mod
    tiktoken_stub._tiktoken = _tiktoken_mod

# --- Stub minimal NLTK tokenizer API to satisfy TextBlob imports ---
nltk_stub = sys.modules.get('nltk') or types.ModuleType('nltk')
tokenize_mod = types.ModuleType('nltk.tokenize')
tokenize_api_mod = types.ModuleType('nltk.tokenize.api')
class _DummyTokenizer: pass
tokenize_api_mod.TokenizerI = _DummyTokenizer
tokenize_mod.api = tokenize_api_mod
nltk_stub.tokenize = tokenize_mod
nltk_stub.data = types.SimpleNamespace(find=lambda path: None)
sys.modules['nltk'] = nltk_stub
sys.modules['nltk.tokenize'] = tokenize_mod
sys.modules['nltk.tokenize.api'] = tokenize_api_mod

# --- Stub TextBlob to prevent heavy deps ---
textblob_mod = types.ModuleType('textblob')
class _DummyTextBlob: pass
textblob_mod.TextBlob = _DummyTextBlob
sys.modules['textblob'] = textblob_mod

# Stub nltk.corpus.stopwords
corpus_mod = types.ModuleType('nltk.corpus')
stopwords_mod = types.ModuleType('nltk.corpus.stopwords')
stopwords_mod.words = lambda lang='english': []
corpus_mod.stopwords = stopwords_mod
sys.modules['nltk.corpus'] = corpus_mod
sys.modules['nltk.corpus.stopwords'] = stopwords_mod

# Stub supabase module early so tools.supabase_client import passes
supabase_stub = types.ModuleType('supabase')
supabase_stub.create_client = lambda url, key: types.SimpleNamespace()
sys.modules['supabase'] = supabase_stub

# --- Stub postgrest with APIResponse early ---
postgrest_stub = types.ModuleType('postgrest')
postgrest_ex_mod = types.ModuleType('postgrest.exceptions')
class _DummyAPIResponse: pass
postgrest_stub.APIResponse = _DummyAPIResponse
postgrest_ex_mod.APIError = type('APIError', (Exception,), {})
postgrest_stub.exceptions = postgrest_ex_mod
sys.modules['postgrest'] = postgrest_stub
sys.modules['postgrest.exceptions'] = postgrest_ex_mod

# --- Stub psycopg2 and its C extension replacement to avoid binary dependency ---
psycopg2_mod = types.ModuleType('psycopg2')
psycopg2_psycopg_mod = types.ModuleType('psycopg2._psycopg')

# Define placeholder objects for attributes expected in C extension
_attrs = [
    'BINARY', 'NUMBER', 'STRING', 'DATETIME', 'ROWID',
    'Binary', 'Date', 'Time', 'Timestamp',
    'DateFromTicks', 'TimeFromTicks', 'TimestampFromTicks',
    'Error', 'Warning', 'DataError', 'DatabaseError', 'ProgrammingError',
    'IntegrityError', 'InterfaceError', 'InternalError', 'NotSupportedError',
    'OperationalError', 'apilevel', 'threadsafety', 'paramstyle', '__version__', '__libpq_version__'
]

for name in _attrs:
    setattr(psycopg2_psycopg_mod, name, object())

# Provide a dummy _connect function
def _dummy_connect(*args, **kwargs):
    # Return minimal connection-like object with cursor method
    class _DummyCursor:
        def execute(self, *a, **k):
            return None
        def fetchone(self):
            return None
        def fetchall(self):
            return []
        def close(self):
            pass

    class _DummyConn:
        def cursor(self, *a, **k):
            return _DummyCursor()
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            pass

    return _DummyConn()

psycopg2_psycopg_mod._connect = _dummy_connect
setattr(psycopg2_psycopg_mod, '_connect', _dummy_connect)

# Expose _connect alias in root module
psycopg2_mod._connect = _dummy_connect
psycopg2_mod.connect = _dummy_connect

# Add reference of _psycopg submodule in psycopg2 module hierarchy
psycopg2_mod.__dict__['_psycopg'] = psycopg2_psycopg_mod

# Install into sys.modules
sys.modules['psycopg2'] = psycopg2_mod
sys.modules['psycopg2._psycopg'] = psycopg2_psycopg_mod

# Ensure werkzeug has __version__ attribute (some distro builds may omit)
import importlib
werkzeug_mod = importlib.import_module('werkzeug') if 'werkzeug' in sys.modules else None
if werkzeug_mod is not None and not hasattr(werkzeug_mod, '__version__'):
    setattr(werkzeug_mod, '__version__', '0.0.0')

# --- Stub OpenAI (removed inadvertently in previous edit) ---
openai_stub = types.ModuleType('openai')

class _DummyEmbeddingResponse:
    def __init__(self):
        self.data = [types.SimpleNamespace(embedding=[])]

class _DummyEmbeddings:
    def create(self, model=None, input=None):
        return _DummyEmbeddingResponse()

class _DummyOpenAIClient:
    def __init__(self, *args, **kwargs):
        self.embeddings = _DummyEmbeddings()

# Basic attributes
openai_stub.OpenAI = _DummyOpenAIClient
openai_stub.RateLimitError = type('RateLimitError', (Exception,), {})
openai_stub.APIError = type('APIError', (Exception,), {})

sys.modules['openai'] = openai_stub

# Provide chat.completions.create upfront
def _dummy_chat_create(*args, **kwargs):
    dummy_choice = types.SimpleNamespace(message=types.SimpleNamespace(content='{}'))
    return types.SimpleNamespace(choices=[dummy_choice])
openai_stub.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=_dummy_chat_create))

# --- Stub scikit-learn minimal API so analysis imports don't pull heavy deps ---
if 'sklearn' not in sys.modules:
    sklearn_root = types.ModuleType('sklearn')
    feature_mod = types.ModuleType('sklearn.feature_extraction')
    text_mod = types.ModuleType('sklearn.feature_extraction.text')

    class _DummyVectorizer:
        def fit(self, X):
            return self

        def transform(self, X):
            return []

        def fit_transform(self, X):
            return []

    text_mod.TfidfVectorizer = _DummyVectorizer
    feature_mod.text = text_mod
    sklearn_root.feature_extraction = feature_mod

    sys.modules['sklearn'] = sklearn_root
    sys.modules['sklearn.feature_extraction'] = feature_mod
    sys.modules['sklearn.feature_extraction.text'] = text_mod
    # Fallback check_build module to satisfy sklearn import path
    check_build_mod = types.ModuleType('sklearn.__check_build')
    sys.modules['sklearn.__check_build'] = check_build_mod

# Stub dateutil as package with parser submodule
dateutil_mod = types.ModuleType('dateutil')
dateutil_mod.__path__ = []  # Mark as package

parser_mod = types.ModuleType('dateutil.parser')
parser_mod.parse = lambda s, *args, **kwargs: None

# Attach submodule to parent
dateutil_mod.parser = parser_mod

sys.modules['dateutil'] = dateutil_mod
sys.modules['dateutil.parser'] = parser_mod

@pytest.fixture()
def app_client(monkeypatch):
    """Create a Flask test client with DEV_AUTO_LOGIN enabled."""
    # Set env vars
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('DEV_AUTO_LOGIN_EMAIL', 'test@example.com')
    monkeypatch.setenv('SUPABASE_URL', 'http://fake.local')
    monkeypatch.setenv('SUPABASE_SERVICE_KEY', 'fake-key')

    # Mock SupabaseClient to avoid real network
    from tools import supabase_client as sb_mod
    class FakeAuthAdmin:
        def get_user_by_email(self, email):
            FakeUser = types.SimpleNamespace(id='uuid-123')
            return types.SimpleNamespace(user=FakeUser)
    class FakeAuth:
        admin = FakeAuthAdmin()
    class FakeSb:
        auth = FakeAuth()
    def fake_create_client(url, key):
        return FakeSb()
    monkeypatch.setattr(sb_mod, 'create_client', lambda url, key: FakeSb())

    # Reload module to apply monkeypatch before import into app
    import app
    importlib.reload(app.__init__)
    app_obj = app.__init__.create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    client = app_obj.test_client()
    yield client


def test_protected_route_redirects_without_login(monkeypatch):
    """/ should redirect to /login when no auto login and not authenticated."""
    monkeypatch.delenv('DEV_AUTO_LOGIN_EMAIL', raising=False)
    from app.__init__ import create_app
    app_obj = create_app({'TESTING': True})
    client = app_obj.test_client()
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_auto_login_access(app_client):
    """DEV_AUTO_LOGIN should grant access to protected route."""
    resp = app_client.get('/')
    assert resp.status_code == 200
    assert b'How&#39;s Lily' in resp.data

# Remove duplicate openai_stub chat assignment (now done above) 