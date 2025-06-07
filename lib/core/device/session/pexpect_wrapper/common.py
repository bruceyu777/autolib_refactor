import re

from lib.services import logger


def clean_by_pattern(original_output, clean_patterns):
    cleaned_output = original_output
    for p_description, pattern in clean_patterns.items():
        cleaned_output = re.sub(pattern, "", original_output)
        if original_output != cleaned_output:
            title = f"*** Clean Pattern '{p_description}' Matched ***"
            delimiter = "*" * len(title)
            logger.debug(
                "\n%s\n%s\nCleaned Content:\n'%s'\n%s",
                delimiter,
                title,
                cleaned_output,
                delimiter,
            )
            original_output = cleaned_output
    return cleaned_output
