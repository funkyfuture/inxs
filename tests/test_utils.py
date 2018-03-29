from inxs.utils import reduce_whitespaces


def test_reduce_whitespaces():
    kooks = "   \n  Will you stay in our lover's story?\n" \
            "If you stay you won't be sorry,\n" \
            "'cause we \t believe in you.\n" \
            "...     \t"
    assert reduce_whitespaces(kooks).startswith('Will')
    assert reduce_whitespaces(kooks).endswith('...')
    assert '\t' in reduce_whitespaces(kooks, '\n')
