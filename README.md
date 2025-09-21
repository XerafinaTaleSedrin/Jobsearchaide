# Automated Remote Job Search Agent

A powerful Python-based tool that automatically searches for remote jobs across multiple Applicant Tracking System (ATS) platforms and job boards, filters results, and generates comprehensive reports in Markdown and PDF formats.

## Features

- **Multi-Platform Search**: Automatically searches 11+ job sites including ATS platforms (Greenhouse, Lever, iCIMS, etc.) and job boards
- **Google Search Integration**: Uses advanced Google search operators with 24-hour time filtering
- **Smart Filtering**:
  - Salary range filtering
  - Keyword exclusions
  - Experience level filtering
  - Remote job verification
- **Duplicate Detection**: Intelligent deduplication across all sources
- **Rich Reports**: Professional Markdown and PDF reports with job summaries and direct links
- **Configurable**: YAML-based configuration with CLI overrides

## Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Setup** (optional):
   ```bash
   python main.py setup
   ```

## Quick Start

### Basic Usage
```bash
# Search for software engineering jobs
python main.py "software engineer"

# Search multiple job titles
python main.py "data scientist" "machine learning engineer"

# Generate PDF report only
python main.py "product manager" --output-format pdf
```

### Advanced Usage
```bash
# Filter by salary range and exclude internships
python main.py "python developer" --salary-min 80000 --salary-max 150000 --exclude-keywords intern

# Dry run to see what would be searched
python main.py "devops engineer" --dry-run

# Verbose output for debugging
python main.py "frontend developer" --verbose
```

## Configuration

The `config.yaml` file controls all search and filtering settings:

### Key Settings

- **Time Filter**: Search jobs posted in last 24 hours (configurable)
- **Job Sites**: 11 pre-configured platforms (extendable)
- **Filtering**: Salary ranges, keyword exclusions, experience levels
- **Output**: Report formats (MD/PDF/both) and styling options

### Google API (Optional)

For enhanced search capabilities, configure Google Custom Search API:

1. Get API key from [Google Custom Search](https://developers.google.com/custom-search/v1/introduction)
2. Update `config.yaml`:
   ```yaml
   google_api:
     api_key: "your_api_key_here"
     search_engine_id: "your_search_engine_id"
   ```

## How It Works

### Search Strategy
The agent uses the LinkedIn article's proven methodology:
- **Google Search Operators**: `site:[domain] "[job title]" AND "remote"`
- **Time Filtering**: Results from last 24 hours only
- **Multi-Threading**: Concurrent searches for speed

### Job Sites Searched
**ATS Platforms:**
- icims.com
- greenhouse.io
- lever.co
- jobvite.io
- ashbyhq.com
- smartrecruiters.com
- myworkdayjobs.com

**Additional Platforms:**
- startup.jobs
- wellfound.com
- builtin.com
- startups.gallery

### Processing Pipeline
1. **Search**: Multi-threaded Google searches across all platforms
2. **Extract**: Scrape job details from posting pages
3. **Filter**: Apply salary, keyword, and remote verification filters
4. **Dedupe**: Remove duplicates using intelligent ID generation
5. **Score**: Calculate relevance scores based on search term matching
6. **Report**: Generate formatted Markdown and/or PDF reports

## Report Output

### Markdown Report
- Clean formatting with job summaries
- Organized by job site
- Direct application links
- Salary and relevance information

### PDF Report
- Professional styling with tables
- Summary statistics
- Top jobs per platform
- Embedded links for applications

## Command Line Options

```bash
Usage: python main.py [OPTIONS] SEARCH_TERMS...

Options:
  -c, --config PATH          Configuration file path
  -f, --output-format        Output format: markdown|pdf|both
  -m, --max-results INTEGER  Maximum results per site
  --salary-min INTEGER       Minimum salary filter (USD)
  --salary-max INTEGER       Maximum salary filter (USD)
  -x, --exclude-keywords     Additional exclusion keywords
  -v, --verbose              Enable detailed logging
  -d, --dry-run              Preview search without executing
  --help                     Show help message
```

## Additional Commands

```bash
# Setup and verify installation
python main.py setup

# List all configured job sites
python main.py list-sites
```

## Output Structure

Reports are saved to `./reports/` directory:
```
reports/
├── job_search_20241221_143022_software_engineer.md
├── job_search_20241221_143022_software_engineer.pdf
└── ...
```

## Customization

### Adding New Job Sites
Edit `config.yaml`:
```yaml
job_sites:
  additional_platforms:
    - "your-new-site.com"
```

### Custom Filters
Modify filtering criteria:
```yaml
filters:
  exclude_keywords:
    - "your-exclusion"
  salary_ranges:
    minimum: 60000
    maximum: 200000
```

## Troubleshooting

### Common Issues

1. **No results found**:
   - Check search terms are relevant
   - Verify 24-hour time filter isn't too restrictive
   - Use `--verbose` flag for debugging

2. **Rate limiting**:
   - Increase `request_delay` in config
   - Reduce `max_results_per_site`

3. **PDF generation fails**:
   - Ensure reportlab is installed: `pip install reportlab`

### Dependencies

Core requirements:
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `pyyaml` - Configuration management
- `click` - CLI interface
- `reportlab` - PDF generation (optional)

## Contributing

The agent is designed for easy extension:
- Add new job sites in `job_searcher.py`
- Enhance filtering in `job_processor.py`
- Customize report formats in `report_generator.py`

## License

Open source - feel free to modify and distribute.

---

*Based on the Google search methodology from Wayan Vota's LinkedIn article about finding hidden remote jobs.*