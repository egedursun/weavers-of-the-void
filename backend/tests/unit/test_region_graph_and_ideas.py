from aerona.cartography.graph import RegionGraph
from aerona.cartography.model import RegionRecord
from aerona.catalog.mind_split import IDEAS, idea_for_beliefs
from tests.engine.society.factories import region_record


def test_a_region_graph_knows_its_regions_their_neighbours_and_the_hops_between() -> None:
    graph = RegionGraph(
        [
            RegionRecord.model_validate(region_record(1, neighbours=[2])),
            RegionRecord.model_validate(region_record(2, neighbours=[3])),
            RegionRecord.model_validate(region_record(3, neighbours=[])),
        ]
    )
    assert 1 in graph and 9 not in graph
    assert graph.neighbours(1) == [2] and graph.neighbours(9) == []
    assert graph.hop_distance(1, 3) == 2 and graph.hop_distance(None, 3) is None


def test_beliefs_lead_to_the_idea_they_fit_best_or_to_none() -> None:
    kind, spec = next(iter(IDEAS.items()))
    strongest = {axis: 100 * weight for axis, weight in spec.beliefs.items()}
    chosen = idea_for_beliefs(strongest)
    assert chosen is not None and sum(strongest.get(axis, 0) * weight for axis, weight in IDEAS[chosen].beliefs.items()) > 0
    assert kind in IDEAS
    assert idea_for_beliefs({}) is None
