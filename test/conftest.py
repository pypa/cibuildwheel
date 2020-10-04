import pytest

import cibuildwheel.windows


@pytest.fixture(autouse=True)
def setup_python(monkeypatch, request):
    try:
        from xdist.plugin import get_xdist_worker_id
        worker_id = get_xdist_worker_id(request)
        monkeypatch.setattr(cibuildwheel.windows, "INSTALL_PATH", 'C:\\cibw\\{}'.format(worker_id))
    except ImportError:
        pass
