import io
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

import pandas as pd
from fpdf import FPDF


class PDFExporter(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(30, 60, 120)
        self.cell(0, 10, 'EMI & Loan Advisory Report', 0, 1, 'C')
        self.set_font('Helvetica', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Generated on {datetime.now().strftime("%d %b %Y %H:%M")}', 0, 1, 'C')
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')
    
    def section_title(self, title: str):
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(30, 60, 120)
        self.cell(0, 8, title, 0, 1, 'L')
        self.set_draw_color(30, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
    
    def key_value(self, key: str, value: str, indent: int = 10):
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(50, 50, 50)
        self.cell(indent, 6, '', 0, 0)
        self.cell(60, 6, key, 0, 0)
        self.set_font('Helvetica', '', 9)
        self.cell(0, 6, value, 0, 1)
    
    def add_table(self, headers: List[str], rows: List[List[str]], col_widths: Optional[List[float]] = None):
        if col_widths is None:
            col_widths = [180 / len(headers)] * len(headers)
        
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(30, 60, 120)
        self.set_text_color(255, 255, 255)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, header, 1, 0, 'C', True)
        self.ln()
        
        self.set_font('Helvetica', '', 8)
        self.set_text_color(50, 50, 50)
        fill = False
        for row in rows:
            if self.get_y() > 260:
                self.add_page()
                self.set_font('Helvetica', 'B', 8)
                self.set_fill_color(30, 60, 120)
                self.set_text_color(255, 255, 255)
                for i, header in enumerate(headers):
                    self.cell(col_widths[i], 7, header, 1, 0, 'C', True)
                self.ln()
                self.set_font('Helvetica', '', 8)
                self.set_text_color(50, 50, 50)
                fill = False
            
            if fill:
                self.set_fill_color(240, 245, 255)
            else:
                self.set_fill_color(255, 255, 255)
            
            for i, cell in enumerate(row):
                align = 'R' if i > 0 else 'L'
                self.cell(col_widths[i], 6, str(cell), 1, 0, align, True)
            self.ln()
            fill = not fill
        self.ln(3)


def generate_pdf_report(export_data: Dict[str, Any]) -> bytes:
    pdf = PDFExporter()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    profile = export_data.get('profile')
    if profile:
        pdf.section_title('User Profile')
        pdf.key_value('Monthly Income:', f"Rs. {profile.get('monthly_income', 0):,.0f}")
        pdf.key_value('Monthly Expenses:', f"Rs. {profile.get('monthly_expenses', 0):,.0f}")
        pdf.key_value('Existing EMIs:', f"Rs. {profile.get('existing_emis', 0):,.0f}")
        pdf.key_value('Age:', str(profile.get('age', 'N/A')))
        pdf.key_value('Employment Type:', profile.get('employment_type', 'N/A'))
        pdf.key_value('Credit Score:', str(profile.get('credit_score', 'N/A')))
        pdf.ln(3)
    
    calculations = export_data.get('calculations', [])
    
    for calc in calculations:
        tool = calc.get('tool', '')
        data = calc.get('data', {})
        timestamp = calc.get('timestamp', '')
        
        if tool == 'calculate_emi':
            pdf.section_title('EMI Calculation')
            pdf.key_value('Calculation Time:', timestamp[:19].replace('T', ' '))
            pdf.key_value('Monthly EMI:', f"Rs. {data.get('monthly_emi', 0):,.2f}")
            pdf.key_value('Total Interest:', f"Rs. {data.get('total_interest', 0):,.2f}")
            pdf.key_value('Total Payment:', f"Rs. {data.get('total_payment', 0):,.2f}")
            pdf.key_value('Principal:', f"Rs. {data.get('principal', 0):,.2f}")
            pdf.key_value('Processing Fee:', f"Rs. {data.get('processing_fee', 0):,.2f}")
            pdf.key_value('Effective Rate:', f"{data.get('effective_rate', 0):.2f}%")
            pdf.ln(3)
        
        elif tool == 'compare_loans':
            pdf.section_title('Loan Comparison')
            pdf.key_value('Comparison Time:', timestamp[:19].replace('T', ' '))
            
            headers = ['Option', 'Principal', 'Rate', 'Tenure', 'EMI', 'Total Interest', 'Total Cost']
            rows = []
            for opt in data.get('comparison_table', []):
                rows.append([
                    opt.get('name', ''),
                    f"Rs. {opt.get('principal', 0):,.0f}",
                    f"{opt.get('annual_rate', 0)}%",
                    f"{opt.get('tenure_years', 0)} yr",
                    f"Rs. {opt.get('monthly_emi', 0):,.0f}",
                    f"Rs. {opt.get('total_interest', 0):,.0f}",
                    f"Rs. {opt.get('total_payment', 0):,.0f}"
                ])
            pdf.add_table(headers, rows, [30, 25, 15, 15, 25, 30, 30])
            
            pdf.key_value('Best Overall:', data.get('best_overall', {}).get('name', ''))
            pdf.key_value('Lowest EMI:', data.get('lowest_emi', {}).get('name', ''))
            pdf.key_value('Lowest Interest:', data.get('lowest_total_interest', {}).get('name', ''))
            pdf.ln(3)
        
        elif tool == 'check_eligibility':
            pdf.section_title('Eligibility Assessment')
            pdf.key_value('Assessment Time:', timestamp[:19].replace('T', ' '))
            status = 'ELIGIBLE' if data.get('eligible') else 'NOT ELIGIBLE'
            pdf.key_value('Status:', status)
            pdf.key_value('Max Loan Amount:', f"Rs. {data.get('max_loan_amount', 0):,.0f}")
            pdf.key_value('Max Affordable EMI:', f"Rs. {data.get('max_emi', 0):,.0f}")
            pdf.key_value('Recommended EMI:', f"Rs. {data.get('recommended_emi', 0):,.0f}")
            pdf.key_value('Recommended Tenure:', f"{data.get('recommended_tenure_years', 0)} years")
            pdf.key_value('DTI Ratio:', f"{data.get('dti_ratio', 0):.1f}%")
            pdf.key_value('FOI Ratio:', f"{data.get('foi_ratio', 0):.1f}%")
            pdf.key_value('Income Multiplier:', f"{data.get('income_multiplier', 0):.1f}x")
            
            notes = data.get('notes', [])
            if notes:
                pdf.ln(2)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(0, 6, 'Notes:', 0, 1)
                pdf.set_font('Helvetica', '', 9)
                for note in notes:
                    pdf.cell(10, 5, '', 0, 0)
                    pdf.multi_cell(0, 5, f"- {note}")
            pdf.ln(3)
        
        elif tool == 'generate_amortization':
            pdf.section_title('Amortization Schedule')
            pdf.key_value('Generation Time:', timestamp[:19].replace('T', ' '))
            
            rows_data = data.get('rows', [])
            if rows_data:
                pdf.key_value('Total Principal:', f"Rs. {data.get('total_principal', 0):,.0f}")
                pdf.key_value('Total Interest:', f"Rs. {data.get('total_interest', 0):,.0f}")
                pdf.key_value('Total Payment:', f"Rs. {data.get('total_payment', 0):,.0f}")
                pdf.key_value('Loan Term:', f"{data.get('loan_term_months', 0)} months")
                pdf.ln(2)
                
                headers = ['Month', 'Opening Bal', 'EMI', 'Principal', 'Interest', 'Closing Bal']
                rows = []
                for row in rows_data[:24]:
                    rows.append([
                        str(row.get('month', '')),
                        f"Rs. {row.get('opening_balance', 0):,.0f}",
                        f"Rs. {row.get('emi', 0):,.0f}",
                        f"Rs. {row.get('principal_paid', 0):,.0f}",
                        f"Rs. {row.get('interest_paid', 0):,.0f}",
                        f"Rs. {row.get('closing_balance', 0):,.0f}"
                    ])
                pdf.add_table(headers, rows, [15, 30, 25, 25, 25, 30])
                
                if len(rows_data) > 24:
                    pdf.key_value('', f"... and {len(rows_data) - 24} more months")
            pdf.ln(3)
        
        elif tool == 'calculate_prepayment_impact':
            pdf.section_title('Prepayment Impact Analysis')
            pdf.key_value('Analysis Time:', timestamp[:19].replace('T', ' '))
            pdf.key_value('Prepayment Amount:', f"Rs. {data.get('prepayment_amount', 0):,.0f}")
            pdf.key_value('Prepayment Month:', str(data.get('prepayment_month', 0)))
            pdf.key_value('Interest Saved:', f"Rs. {data.get('interest_saved', 0):,.0f}")
            pdf.key_value('Months Reduced:', str(data.get('months_reduced', 0)))
            pdf.key_value('New Tenure:', f"{data.get('new_tenure_months', 0)} months")
            pdf.key_value('Effective Savings:', f"Rs. {data.get('effective_savings', 0):,.0f}")
            
            orig = data.get('original_schedule', {})
            new = data.get('new_schedule', {})
            pdf.key_value('Original Total Interest:', f"Rs. {orig.get('total_interest', 0):,.0f}")
            pdf.key_value('New Total Interest:', f"Rs. {new.get('total_interest', 0):,.0f}")
            pdf.ln(3)
        
        elif tool == 'calculate_affordability':
            pdf.section_title('Affordability Assessment')
            pdf.key_value('Assessment Time:', timestamp[:19].replace('T', ' '))
            pdf.key_value('Max Affordable Loan:', f"Rs. {data.get('max_principal', 0):,.0f}")
            pdf.key_value('Recommended EMI:', f"Rs. {data.get('recommended_emi', 0):,.0f}")
            pdf.key_value('Comfortable EMI:', f"Rs. {data.get('comfortable_emi', 0):,.0f}")
            pdf.key_value('Stretch EMI:', f"Rs. {data.get('stretch_emi', 0):,.0f}")
            pdf.key_value('DTI at Recommended:', f"{data.get('dti_at_recommended', 0):.1f}%")
            pdf.key_value('DTI at Stretch:', f"{data.get('dti_at_stretch', 0):.1f}%")
            pdf.key_value('Assumed Rate:', f"{data.get('interest_rate', 0)}%")
            pdf.key_value('Tenure:', f"{data.get('tenure_years', 0)} years")
            pdf.ln(3)
    
    output = io.BytesIO()
    pdf.output(output)
    return output.getvalue()


def generate_excel_report(export_data: Dict[str, Any]) -> bytes:
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        profile = export_data.get('profile')
        if profile:
            profile_df = pd.DataFrame([{
                'Field': k.replace('_', ' ').title(),
                'Value': v
            } for k, v in profile.items() if v is not None])
            profile_df.to_excel(writer, sheet_name='Profile', index=False)
        
        calculations = export_data.get('calculations', [])
        
        for idx, calc in enumerate(calculations):
            tool = calc.get('tool', '')
            data = calc.get('data', {})
            timestamp = calc.get('timestamp', '')
            
            sheet_name = tool[:31]
            if len(calculations) > 1:
                sheet_name = f"{tool[:25]}_{idx+1}"
            
            if tool == 'calculate_emi':
                df = pd.DataFrame([{
                    'Parameter': 'Monthly EMI',
                    'Value': f"Rs. {data.get('monthly_emi', 0):,.2f}"
                }, {
                    'Parameter': 'Total Interest',
                    'Value': f"Rs. {data.get('total_interest', 0):,.2f}"
                }, {
                    'Parameter': 'Total Payment',
                    'Value': f"Rs. {data.get('total_payment', 0):,.2f}"
                }, {
                    'Parameter': 'Principal',
                    'Value': f"Rs. {data.get('principal', 0):,.2f}"
                }, {
                    'Parameter': 'Processing Fee',
                    'Value': f"Rs. {data.get('processing_fee', 0):,.2f}"
                }, {
                    'Parameter': 'Effective Annual Rate',
                    'Value': f"{data.get('effective_rate', 0):.2f}%"
                }, {
                    'Parameter': 'Calculation Time',
                    'Value': timestamp[:19].replace('T', ' ')
                }])
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            elif tool == 'compare_loans':
                comparison_table = data.get('comparison_table', [])
                if comparison_table:
                    df = pd.DataFrame(comparison_table)
                    df.columns = [c.replace('_', ' ').title() for c in df.columns]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            elif tool == 'check_eligibility':
                df = pd.DataFrame([{
                    'Parameter': 'Eligible',
                    'Value': 'Yes' if data.get('eligible') else 'No'
                }, {
                    'Parameter': 'Max Loan Amount',
                    'Value': f"Rs. {data.get('max_loan_amount', 0):,.0f}"
                }, {
                    'Parameter': 'Max Affordable EMI',
                    'Value': f"Rs. {data.get('max_emi', 0):,.0f}"
                }, {
                    'Parameter': 'Recommended EMI',
                    'Value': f"Rs. {data.get('recommended_emi', 0):,.0f}"
                }, {
                    'Parameter': 'Recommended Tenure (Years)',
                    'Value': data.get('recommended_tenure_years', 0)
                }, {
                    'Parameter': 'DTI Ratio (%)',
                    'Value': f"{data.get('dti_ratio', 0):.1f}"
                }, {
                    'Parameter': 'FOI Ratio (%)',
                    'Value': f"{data.get('foi_ratio', 0):.1f}"
                }, {
                    'Parameter': 'Income Multiplier',
                    'Value': f"{data.get('income_multiplier', 0):.1f}x"
                }, {
                    'Parameter': 'Loan to Value (%)',
                    'Value': f"{data.get('loan_to_value_ratio', 0):.1f}" if data.get('loan_to_value_ratio') else 'N/A'
                }, {
                    'Parameter': 'Assessment Time',
                    'Value': timestamp[:19].replace('T', ' ')
                }])
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                notes = data.get('notes', [])
                if notes:
                    notes_df = pd.DataFrame({'Notes': notes})
                    notes_df.to_excel(writer, sheet_name=f"{sheet_name}_Notes", index=False)
            
            elif tool == 'generate_amortization':
                rows_data = data.get('rows', [])
                if rows_data:
                    summary_df = pd.DataFrame([{
                        'Parameter': 'Total Principal',
                        'Value': f"Rs. {data.get('total_principal', 0):,.0f}"
                    }, {
                        'Parameter': 'Total Interest',
                        'Value': f"Rs. {data.get('total_interest', 0):,.0f}"
                    }, {
                        'Parameter': 'Total Payment',
                        'Value': f"Rs. {data.get('total_payment', 0):,.0f}"
                    }, {
                        'Parameter': 'Loan Term (Months)',
                        'Value': data.get('loan_term_months', 0)
                    }, {
                        'Parameter': 'Generation Time',
                        'Value': timestamp[:19].replace('T', ' ')
                    }])
                    summary_df.to_excel(writer, sheet_name=f"{sheet_name}_Summary", index=False)
                    
                    schedule_df = pd.DataFrame(rows_data)
                    schedule_df.columns = [c.replace('_', ' ').title() for c in schedule_df.columns]
                    schedule_df.to_excel(writer, sheet_name=f"{sheet_name}_Schedule", index=False)
            
            elif tool == 'calculate_prepayment_impact':
                orig = data.get('original_schedule', {})
                new = data.get('new_schedule', {})
                
                summary_df = pd.DataFrame([{
                    'Parameter': 'Prepayment Amount',
                    'Value': f"Rs. {data.get('prepayment_amount', 0):,.0f}"
                }, {
                    'Parameter': 'Prepayment Month',
                    'Value': data.get('prepayment_month', 0)
                }, {
                    'Parameter': 'Interest Saved',
                    'Value': f"Rs. {data.get('interest_saved', 0):,.0f}"
                }, {
                    'Parameter': 'Months Reduced',
                    'Value': data.get('months_reduced', 0)
                }, {
                    'Parameter': 'New Tenure (Months)',
                    'Value': data.get('new_tenure_months', 0)
                }, {
                    'Parameter': 'Effective Savings',
                    'Value': f"Rs. {data.get('effective_savings', 0):,.0f}"
                }, {
                    'Parameter': 'Original Total Interest',
                    'Value': f"Rs. {orig.get('total_interest', 0):,.0f}"
                }, {
                    'Parameter': 'New Total Interest',
                    'Value': f"Rs. {new.get('total_interest', 0):,.0f}"
                }, {
                    'Parameter': 'Analysis Time',
                    'Value': timestamp[:19].replace('T', ' ')
                }])
                summary_df.to_excel(writer, sheet_name=f"{sheet_name}_Summary", index=False)
                
                for label, schedule in [('Original', orig), ('New', new)]:
                    rows = schedule.get('rows', [])
                    if rows:
                        df = pd.DataFrame(rows)
                        df.columns = [c.replace('_', ' ').title() for c in df.columns]
                        df.to_excel(writer, sheet_name=f"{sheet_name}_{label}", index=False)
            
            elif tool == 'calculate_affordability':
                df = pd.DataFrame([{
                    'Parameter': 'Max Affordable Loan',
                    'Value': f"Rs. {data.get('max_principal', 0):,.0f}"
                }, {
                    'Parameter': 'Recommended EMI',
                    'Value': f"Rs. {data.get('recommended_emi', 0):,.0f}"
                }, {
                    'Parameter': 'Comfortable EMI',
                    'Value': f"Rs. {data.get('comfortable_emi', 0):,.0f}"
                }, {
                    'Parameter': 'Stretch EMI',
                    'Value': f"Rs. {data.get('stretch_emi', 0):,.0f}"
                }, {
                    'Parameter': 'DTI at Recommended (%)',
                    'Value': f"{data.get('dti_at_recommended', 0):.1f}"
                }, {
                    'Parameter': 'DTI at Stretch (%)',
                    'Value': f"{data.get('dti_at_stretch', 0):.1f}"
                }, {
                    'Parameter': 'Assumed Rate (%)',
                    'Value': data.get('interest_rate', 0)
                }, {
                    'Parameter': 'Tenure (Years)',
                    'Value': data.get('tenure_years', 0)
                }, {
                    'Parameter': 'Assessment Time',
                    'Value': timestamp[:19].replace('T', ' ')
                }])
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    return output.getvalue()


def generate_reports(export_data: Dict[str, Any], formats: List[str] = ['pdf', 'excel']) -> Dict[str, bytes]:
    results = {}
    if 'pdf' in formats:
        results['pdf'] = generate_pdf_report(export_data)
    if 'excel' in formats:
        results['excel'] = generate_excel_report(export_data)
    return results