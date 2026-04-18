import pytest

from gameofgit.quests import all_quests


@pytest.fixture(params=list(all_quests()), ids=lambda q: q.slug)
def quest(request):
    return request.param
