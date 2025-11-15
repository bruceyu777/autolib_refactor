#!/usr/bin/env python3
"""
Performance profiling for compiler with hundreds of scripts.
"""

import cProfile
import io
import pstats
import random

# Add project root to path
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.core.compiler.lexer import Lexer
from lib.core.compiler.parser import Parser
from lib.core.compiler.settings import SYNTAX_DEFINITION_FILEPATH

# Sample script templates for testing
SCRIPT_TEMPLATES = [
    # Simple command script
    """[FGT1]
config system global
    set hostname test-fgt
end
show system status
""",
    # API heavy script
    """[FGT1]
<setvar var1 "test_value">
<expect -e "login:" -for QA001 -t 10>
<sendline -line "admin" -for QA002>
<expect -e "#" -for QA003 -t 5>
<report -qaid QA004 -result pass>
""",
    # More APIs
    """[FGT1]
<setvar ip_addr "192.168.1.1">
<setvar netmask "255.255.255.0">
<setvar gateway "192.168.1.254">
<expect -e "FGT" -for QA010 -t 30>
<sendline -line "config system interface" -for QA011>
<expect -e "#" -for QA012>
<report -qaid QA013 -result pass>
""",
    # Mixed script
    """[FGT1]
<setvar device_ip "10.0.0.1">
config system interface
    edit port1
        set ip 10.0.0.1 255.255.255.0
    next
end
<expect -e "OK" -for QA100 -t 5>
<report -qaid QA101 -result pass>
""",
    # Command heavy
    """[FGT1]
config system global
    set hostname fgt-test-01
    set admin-sport 443
    set admin-ssh-port 22
    set admintimeout 60
end
show system status
show system interface
get system status
""",
]


def generate_test_scripts(count=100, output_dir=None):
    """Generate test scripts for performance testing."""
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="perf_test_"))
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    script_files = []
    for i in range(count):
        # Randomly select and combine templates
        script_content = random.choice(SCRIPT_TEMPLATES)

        # Add more sections for larger scripts
        if i % 5 == 0:
            script_content += f"\n[FGT2]\n{random.choice(SCRIPT_TEMPLATES)}"

        script_file = output_dir / f"test_script_{i:04d}.fos"
        with open(script_file, "w") as f:
            f.write(script_content)
        script_files.append(script_file)

    return script_files


def measure_single_compilation(script_file):
    """Measure compilation time for a single script."""
    start = time.perf_counter()

    # Lexer phase
    lexer = Lexer(str(script_file))
    tokens, lines = lexer.parse()

    lexer_time = time.perf_counter() - start

    # Parser phase
    parser_start = time.perf_counter()
    parser = Parser(str(script_file), tokens, lines)
    vm_codes, devices, called_files = parser.run()
    parser_time = time.perf_counter() - parser_start

    total_time = time.perf_counter() - start

    return {
        "lexer_time": lexer_time,
        "parser_time": parser_time,
        "total_time": total_time,
        "tokens": len(tokens),
        "vm_codes": len(vm_codes),
    }


def measure_bulk_compilation(script_files):
    """Measure compilation time for multiple scripts."""
    results = []

    start_total = time.perf_counter()

    for script_file in script_files:
        result = measure_single_compilation(script_file)
        result["file"] = script_file.name
        results.append(result)

    total_time = time.perf_counter() - start_total

    return results, total_time


def profile_compilation(script_files, profile_file="compilation.prof"):
    """Profile compilation with cProfile."""
    pr = cProfile.Profile()
    pr.enable()

    for script_file in script_files:
        lexer = Lexer(str(script_file))
        tokens, lines = lexer.parse()
        parser = Parser(str(script_file), tokens, lines)
        vm_codes, devices, called_files = parser.run()

    pr.disable()

    # Save profile
    pr.dump_stats(profile_file)

    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(30)  # Top 30 functions

    return s.getvalue()


def analyze_schema_loading():
    """Analyze schema loading performance."""

    # Cold load (first time)
    start = time.perf_counter()
    with open(SYNTAX_DEFINITION_FILEPATH, "r") as f:
        import json

        schema = json.load(f)
    cold_load = time.perf_counter() - start

    # Warm loads (subsequent times)
    warm_times = []
    for _ in range(10):
        start = time.perf_counter()
        with open(SYNTAX_DEFINITION_FILEPATH, "r") as f:
            schema = json.load(f)
        warm_times.append(time.perf_counter() - start)

    avg_warm = sum(warm_times) / len(warm_times)

    return {
        "cold_load_ms": cold_load * 1000,
        "avg_warm_load_ms": avg_warm * 1000,
        "schema_size_kb": Path(SYNTAX_DEFINITION_FILEPATH).stat().st_size / 1024,
        "api_count": len(schema.get("apis", {})),
        "valid_commands": len(schema.get("valid_commands", [])),
        "keywords": len(schema.get("keywords", {})),
    }


def print_results(results, total_time, schema_stats, profile_output):
    """Print formatted performance results."""
    print("=" * 80)
    print("COMPILER PERFORMANCE ANALYSIS")
    print("=" * 80)

    # Schema loading
    print("\n1. Schema Loading Performance")
    print("-" * 80)
    print(f"Schema file size:      {schema_stats['schema_size_kb']:.2f} KB")
    print(f"APIs defined:          {schema_stats['api_count']}")
    print(f"Valid commands:        {schema_stats['valid_commands']}")
    print(f"Keywords:              {schema_stats['keywords']}")
    print(f"Cold load time:        {schema_stats['cold_load_ms']:.3f} ms")
    print(f"Avg warm load time:    {schema_stats['avg_warm_load_ms']:.3f} ms")

    # Compilation stats
    print("\n2. Compilation Performance")
    print("-" * 80)
    print(f"Total scripts:         {len(results)}")
    print(f"Total time:            {total_time:.3f} seconds")
    print(f"Avg time per script:   {total_time / len(results) * 1000:.3f} ms")
    print(f"Scripts per second:    {len(results) / total_time:.2f}")

    # Breakdown
    total_lexer = sum(r["lexer_time"] for r in results)
    total_parser = sum(r["parser_time"] for r in results)

    print(f"\nPhase breakdown:")
    print(f"  Lexer:  {total_lexer:.3f}s ({total_lexer/total_time*100:.1f}%)")
    print(f"  Parser: {total_parser:.3f}s ({total_parser/total_time*100:.1f}%)")

    # Slowest scripts
    print("\n3. Slowest Scripts (Top 10)")
    print("-" * 80)
    slowest = sorted(results, key=lambda x: x["total_time"], reverse=True)[:10]
    for i, r in enumerate(slowest, 1):
        print(
            f"{i:2d}. {r['file']:30s} {r['total_time']*1000:7.3f}ms "
            f"(tokens:{r['tokens']:4d}, vm_codes:{r['vm_codes']:4d})"
        )

    # Profile
    print("\n4. Hot Spots (Top 30 Functions)")
    print("-" * 80)
    print(profile_output)

    # Performance issues
    print("\n5. Potential Issues")
    print("-" * 80)

    issues = []

    # Check if any script is too slow
    if any(r["total_time"] > 0.1 for r in results):  # > 100ms
        slow_count = sum(1 for r in results if r["total_time"] > 0.1)
        issues.append(f"⚠️  {slow_count} scripts took > 100ms to compile")

    # Check lexer vs parser balance
    if total_lexer / total_time > 0.7:
        issues.append(
            f"⚠️  Lexer takes {total_lexer/total_time*100:.1f}% of time (regex bottleneck?)"
        )

    # Check schema load time
    if schema_stats["cold_load_ms"] > 50:
        issues.append(
            f"⚠️  Schema cold load time is {schema_stats['cold_load_ms']:.1f}ms (consider caching)"
        )

    if not issues:
        print("✅ No obvious performance issues detected")
    else:
        for issue in issues:
            print(issue)

    print("\n" + "=" * 80)


def main():
    """Main performance test."""
    print("Generating test scripts...")
    script_files = generate_test_scripts(count=100)

    print(f"Analyzing schema loading performance...")
    schema_stats = analyze_schema_loading()

    print(f"Compiling {len(script_files)} scripts...")
    results, total_time = measure_bulk_compilation(script_files)

    print("Profiling compilation...")
    profile_output = profile_compilation(script_files[:20])  # Profile subset

    print_results(results, total_time, schema_stats, profile_output)

    # Cleanup
    import shutil

    shutil.rmtree(script_files[0].parent)
    print(f"\nCleaned up temporary files from {script_files[0].parent}")


if __name__ == "__main__":
    main()
