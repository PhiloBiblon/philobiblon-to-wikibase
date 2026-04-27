"""
test_prompt_cache.py — verify Anthropic prompt caching is working.

Makes 5 calls with the same system prompt and prints cache_creation_input_tokens
and cache_read_input_tokens for each. Expected pattern:
  call 1: cache_creation > 0, cache_read = 0  (writes cache)
  calls 2-5: cache_creation = 0, cache_read > 0  (hits cache)

Usage (from pb2wb/):
    python test_prompt_cache.py
    python test_prompt_cache.py --model claude-sonnet-4-6
"""

import argparse
import os
import sys
import time

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, dir_path)

from prop_migration.generate_basis_mapping import _LLM_SYSTEM_PROMPT, _load_env

TEST_INPUTS = [
    "Faulhaber",
    "Norton 1978:60",
    "BNE MSS/7811",
    "Beltrán 1997:27n",
    "Dutton 1990-91",
]

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--model', default='claude-sonnet-4-6')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Seconds between calls (default: 1.0)')
    args = parser.parse_args()

    _load_env()
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        sys.exit('Fatal: ANTHROPIC_API_KEY not set. Add it to .qs_env.')

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    print(f'Model: {args.model}')
    print(f'System prompt: {len(_LLM_SYSTEM_PROMPT)} chars (~{len(_LLM_SYSTEM_PROMPT)//4} tokens)')
    print(f'{"call":<6} {"input":>8} {"cache_create":>14} {"cache_read":>12} {"output":>8}  result')
    print('-' * 75)

    cache_hits = cache_misses = 0
    for i, basis in enumerate(TEST_INPUTS, 1):
        if i > 1:
            time.sleep(args.delay)
        response = client.messages.create(
            model=args.model,
            max_tokens=64,
            system=[{
                'type': 'text',
                'text': _LLM_SYSTEM_PROMPT,
                'cache_control': {'type': 'ephemeral'},
            }],
            messages=[{'role': 'user', 'content': basis}],
        )
        u = response.usage
        created = getattr(u, 'cache_creation_input_tokens', 0) or 0
        read    = getattr(u, 'cache_read_input_tokens', 0) or 0
        result  = response.content[0].text.strip()[:40]
        hit = read > 0
        if hit:
            cache_hits += 1
        else:
            cache_misses += 1
        marker = '✓ HIT' if hit else ('WRITE' if created > 0 else '✗ MISS')
        print(f'{i:<6} {u.input_tokens:>8} {created:>14} {read:>12} {u.output_tokens:>8}  [{marker}] {basis!r}')

    print('-' * 75)
    print(f'Cache hits: {cache_hits}/5  misses: {cache_misses}/5')
    if cache_hits >= 4:
        print('✓ Prompt caching is working.')
    elif cache_hits == 0:
        print('✗ Caching not working — check token count and cache_control placement.')
    else:
        print('? Partial hits — may be flaky or TTL expiry between calls.')

if __name__ == '__main__':
    main()
