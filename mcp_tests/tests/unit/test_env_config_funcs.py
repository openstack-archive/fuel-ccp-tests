import copy

import pytest

from mcp_tests.helpers import env_config as funcs

# Test data for funcs.return_obj
testdata1 = [
    ([], {}),
    ([0], [{}]),
    ([1], [None, {}]),
    ([4, 1], [None, None, None, None, [None, {}]]),
    (
        [3, 1, 6],
        [None, None, None, [None, [None, None, None, None, None, None, {}]]]
    ),
    (
        [-1, -3, 0],
        [[[{}], None, None]]
    ),
    (
        [-1, 1, -2],
        [[None, [{}, None]]]
    ),
]

# Test data for funcs.set_value_for_dict_by_keypath
some_dict = {}
sample1 = {'params': {'settings': {'version': 3}}}
sample2 = copy.deepcopy(sample1)
sample2.update({'env_name': 'mcp_test'})
sample3 = copy.deepcopy(sample2)
sample3.update(
    {
        'groups': [
            {
                'nodes': [
                    None,
                    {
                        'volumes': [
                            {'source_image': 'some_path'}
                        ]
                    }
                ]
            }
        ]
    }
)
testdata2 = [
    (some_dict, 'params.settings.version', 3, sample1),
    (some_dict, 'env_name', 'mcp_test', sample2),
    (
        some_dict,
        'groups[0].nodes[1].volumes[0].source_image',
        'some_path',
        sample3
    )
]

# Test data for funcs.list_update
testdata3 = [
    ([None, None, None], [2], 'Test', [None, None, 'Test']),
    ([None, None, None], [-1], 'Test', [None, None, 'Test']),
    ([None, [None, [None]]], [1, 1, 0], 'Test', [None, [None, ['Test']]]),
    ([None, [None, [None]]], [-1, 1, 0], 'Test', [None, [None, ['Test']]]),
    ([None, [None, [None]]], [-1, -1, 0], 'Test', [None, [None, ['Test']]]),
    ([None, [None, [None]]], [-1, -1, -1], 'Test', [None, [None, ['Test']]]),
]

sample_list = [
    "string",
    [
        "sublist string",
    ],
    {"index": 2, "value": "dict"}
]
list_update_fail = [
    (sample_list, [0, 1], "test_fail"),
    (sample_list, [1, 1], "test_fail"),
    (sample_list, [1, 1], "test_fail"),
    (sample_list, [0, [2]], "test_fail"),
    (sample_list, [0, None], "test_fail"),
    (sample_list, ["a"], "test_fail")
]

sample_dict = {"root": {"subroot": {"list": ["Test", "value", [1]]}}}
keypath_fail = [
    (sample_dict, "root.subroot.list[2][1]", 3, True),
    (sample_dict, "root.subroot.list[1][0]", 3, True),
    (sample_dict, "root.subroot[0]", 3, True),
    (sample_dict, "root.subroot.undefinedkey", 3, False),
]


@pytest.mark.parametrize("x,exp", testdata1)
@pytest.mark.unit_tests
@pytest.mark.return_obj
def test_return_obj_ok(x, exp):
    assert funcs.return_obj(x) == exp


@pytest.mark.xfail(strict=True)
@pytest.mark.parametrize("x", ["test_fail", [[-1]], ["test_fail"], [0, [3]]])
@pytest.mark.unit_tests
@pytest.mark.return_obj
def test_return_obj_fail(x):
    result = funcs.return_obj(x)
    return result


@pytest.mark.parametrize("source,keypath,value,exp", testdata2)
@pytest.mark.unit_tests
@pytest.mark.set_value_for_dict_by_keypath
def test_set_value_for_dict_by_keypath_ok(source, keypath, value, exp):
    funcs.set_value_for_dict_by_keypath(source, paths=keypath, value=value)
    assert source == exp


@pytest.mark.xfail(strict=True)
@pytest.mark.parametrize("source,keypath,value,make_new", keypath_fail)
@pytest.mark.set_value_for_dict_by_keypath
@pytest.mark.unit_tests
def test_set_value_for_dict_by_keypath_fail(source, keypath, value, make_new):
    funcs.set_value_for_dict_by_keypath(source, paths=keypath, value=value,
                                        new_on_missing=make_new)


@pytest.mark.parametrize('obj,indexes,value,exp', testdata3)
@pytest.mark.unit_tests
@pytest.mark.list_update
def test_list_update_ok(obj, indexes, value, exp):
    funcs.list_update(obj, indexes, value)
    assert obj == exp


@pytest.mark.xfail(strict=True)
@pytest.mark.parametrize('obj,indexes,value', list_update_fail)
@pytest.mark.list_update
@pytest.mark.unit_tests
def test_list_update_fail(obj, indexes, value):
    funcs.list_update(obj, indexes, value)
