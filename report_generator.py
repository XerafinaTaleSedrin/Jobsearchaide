"""Report generation for job search results in Markdown and PDF formats."""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from job_processor import ProcessedJob
from config import Config

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates formatted reports from processed job data."""

    def __init__(self, config: Config):
        """Initialize the report generator with configuration."""
        self.config = config

    def generate_reports(self, jobs: List[ProcessedJob], search_terms: List[str]) -> Dict[str, str]:
        """Generate reports in configured formats and return file paths."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        search_term_str = '_'.join(search_terms).replace(' ', '_').replace('/', '_')[:50]

        # Generate base filename
        filename_base = self.config.output.filename_template.format(
            timestamp=timestamp,
            search_term=search_term_str
        )

        generated_files = {}

        # Generate Markdown report
        if self.config.output.format in ['markdown', 'both']:
            md_file = self._generate_markdown_report(jobs, search_terms, filename_base)
            generated_files['markdown'] = md_file

        # Generate PDF report
        if self.config.output.format in ['pdf', 'both']:
            pdf_file = self._generate_pdf_report(jobs, search_terms, filename_base)
            generated_files['pdf'] = pdf_file

        return generated_files

    def _generate_markdown_report(self, jobs: List[ProcessedJob], search_terms: List[str], filename_base: str) -> str:
        """Generate a Markdown report."""
        md_filename = os.path.join(self.config.output.output_dir, f"{filename_base}.md")

        try:
            with open(md_filename, 'w', encoding='utf-8') as f:
                # Write header
                f.write(self._get_markdown_header(jobs, search_terms))

                # Write summary statistics
                f.write(self._get_summary_section(jobs, search_terms))

                # Group jobs by source site
                jobs_by_site = self._group_jobs_by_site(jobs)

                # Write jobs organized by site
                for site, site_jobs in jobs_by_site.items():
                    f.write(f"\n## {site.title()} ({len(site_jobs)} jobs)\n\n")

                    for job in sorted(site_jobs, key=lambda x: x.relevance_score, reverse=True):
                        f.write(self._format_job_markdown(job))

                # Write footer
                f.write(self._get_markdown_footer())

            logger.info(f"Markdown report generated: {md_filename}")
            return md_filename

        except Exception as e:
            logger.error(f"Error generating Markdown report: {e}")
            return ""

    def _generate_pdf_report(self, jobs: List[ProcessedJob], search_terms: List[str], filename_base: str) -> str:
        """Generate a PDF report."""
        pdf_filename = os.path.join(self.config.output.output_dir, f"{filename_base}.pdf")

        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors

            doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=30,
                textColor=colors.darkblue
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                spaceBefore=20,
                textColor=colors.darkblue
            )

            job_title_style = ParagraphStyle(
                'JobTitle',
                parent=styles['Heading3'],
                fontSize=12,
                spaceAfter=6,
                spaceBefore=12,
                textColor=colors.darkred
            )

            story = []

            # Title
            title = f"Remote Job Search Report - {', '.join(search_terms)}"
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 20))

            # Summary
            summary_data = self._get_summary_data(jobs, search_terms)
            story.append(Paragraph("Summary", heading_style))

            summary_table_data = [
                ['Search Terms', ', '.join(search_terms)],
                ['Total Jobs Found', str(len(jobs))],
                ['Search Date', datetime.now().strftime('%Y-%m-%d %H:%M')],
                ['Sites Searched', str(len(set(job.source_site for job in jobs)))]
            ]

            if jobs:
                avg_relevance = sum(job.relevance_score for job in jobs) / len(jobs)
                summary_table_data.append(['Average Relevance', f"{avg_relevance:.2f}"])

            summary_table = Table(summary_table_data, colWidths=[2*inch, 3*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(summary_table)
            story.append(Spacer(1, 20))

            # Jobs by site
            jobs_by_site = self._group_jobs_by_site(jobs)

            for site, site_jobs in jobs_by_site.items():
                story.append(Paragraph(f"{site.title()} ({len(site_jobs)} jobs)", heading_style))

                for job in sorted(site_jobs, key=lambda x: x.relevance_score, reverse=True)[:10]:  # Limit to top 10 per site
                    story.append(Paragraph(job.title, job_title_style))

                    job_data = [
                        ['Company', job.company or 'Not specified'],
                        ['Location', job.location or 'Remote'],
                        ['Salary', job.salary or 'Not specified'],
                        ['Relevance', f"{job.relevance_score:.2f}"],
                        ['Link', f'<link href="{job.url}">Apply Here</link>']
                    ]

                    job_table = Table(job_data, colWidths=[1*inch, 4*inch])
                    job_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('GRID', (0, 0), (-1, -1), 1, colors.gray),
                        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)
                    ]))

                    story.append(job_table)

                    if self.config.output.include_summaries and job.summary:
                        summary_text = f"<b>Summary:</b> {job.summary}"
                        story.append(Paragraph(summary_text, styles['Normal']))

                    story.append(Spacer(1, 12))

            # Build PDF
            doc.build(story)

            logger.info(f"PDF report generated: {pdf_filename}")
            return pdf_filename

        except ImportError:
            logger.warning("ReportLab not available for PDF generation. Install with: pip install reportlab")
            return ""
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            return ""

    def _get_markdown_header(self, jobs: List[ProcessedJob], search_terms: List[str]) -> str:
        """Generate Markdown report header."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f"""# Remote Job Search Report

**Search Terms:** {', '.join(search_terms)}
**Generated:** {timestamp}
**Total Jobs Found:** {len(jobs)}

---

"""

    def _get_summary_section(self, jobs: List[ProcessedJob], search_terms: List[str]) -> str:
        """Generate summary statistics section."""
        if not jobs:
            return "## Summary\n\nNo jobs found matching the search criteria.\n\n"

        summary_data = self._get_summary_data(jobs, search_terms)

        sites_breakdown = self._group_jobs_by_site(jobs)
        site_stats = []
        for site, site_jobs in sites_breakdown.items():
            avg_relevance = sum(job.relevance_score for job in site_jobs) / len(site_jobs)
            site_stats.append(f"- **{site}**: {len(site_jobs)} jobs (avg relevance: {avg_relevance:.2f})")

        salary_info = self._get_salary_summary(jobs)

        return f"""## Summary

- **Total Jobs:** {len(jobs)}
- **Unique Companies:** {len(set(job.company for job in jobs if job.company))}
- **Average Relevance Score:** {summary_data['avg_relevance']:.2f}
- **Sites Searched:** {len(sites_breakdown)}

### Jobs by Site
{chr(10).join(site_stats)}

### Salary Information
{salary_info}

---

"""

    def _get_summary_data(self, jobs: List[ProcessedJob], search_terms: List[str]) -> Dict:
        """Get summary statistics."""
        if not jobs:
            return {
                'total_jobs': 0,
                'avg_relevance': 0,
                'unique_companies': 0,
                'sites_count': 0
            }

        return {
            'total_jobs': len(jobs),
            'avg_relevance': sum(job.relevance_score for job in jobs) / len(jobs),
            'unique_companies': len(set(job.company for job in jobs if job.company)),
            'sites_count': len(set(job.source_site for job in jobs))
        }

    def _get_salary_summary(self, jobs: List[ProcessedJob]) -> str:
        """Generate salary summary information."""
        jobs_with_salary = [job for job in jobs if job.salary_min and job.salary_max]

        if not jobs_with_salary:
            return "- No salary information available"

        salaries = [(job.salary_min + job.salary_max) / 2 for job in jobs_with_salary]
        min_salary = min(salaries)
        max_salary = max(salaries)
        avg_salary = sum(salaries) / len(salaries)

        return f"""- **Jobs with Salary Info:** {len(jobs_with_salary)} out of {len(jobs)}
- **Salary Range:** ${min_salary:,.0f} - ${max_salary:,.0f}
- **Average Salary:** ${avg_salary:,.0f}"""

    def _group_jobs_by_site(self, jobs: List[ProcessedJob]) -> Dict[str, List[ProcessedJob]]:
        """Group jobs by source site."""
        jobs_by_site = {}
        for job in jobs:
            site = job.source_site or 'Unknown'
            if site not in jobs_by_site:
                jobs_by_site[site] = []
            jobs_by_site[site].append(job)

        # Sort sites by job count
        return dict(sorted(jobs_by_site.items(), key=lambda x: len(x[1]), reverse=True))

    def _format_job_markdown(self, job: ProcessedJob) -> str:
        """Format a single job for Markdown output."""
        company_info = f" at **{job.company}**" if job.company else ""
        location_info = f" | **Location:** {job.location}" if job.location else ""
        salary_info = f" | **Salary:** {job.salary}" if job.salary else ""
        relevance_info = f" | **Relevance:** {job.relevance_score:.2f}"

        result = f"### {job.title}{company_info}\n\n"
        result += f"**🔗 [Apply Here]({job.url})**{location_info}{salary_info}{relevance_info}\n\n"

        if self.config.output.include_summaries and job.summary:
            result += f"**Summary:** {job.summary}\n\n"

        if job.requirements:
            result += f"**Key Requirements:** {job.requirements}\n\n"

        result += "---\n\n"

        return result

    def _get_markdown_footer(self) -> str:
        """Generate Markdown report footer."""
        return f"""
---

*Report generated by Automated Job Search Agent*
*Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*
"""