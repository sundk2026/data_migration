
import logging
import pandas as pd
from datetime import datetime
import logging

from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment,PatternFill
from collections import defaultdict
from time import strftime
from time import gmtime
import io

class SummaryReport:
    string_truncate_object=[]
    duplicate_geom=[]
    summary_rpt=[]
    bypassed_data=[]
    fields_issues=[]    
    def __init__(self, report_file_path):
        self.report_file_path = report_file_path
        self.summary_rpt.append(["records_skipped_due_to_parent_data_mismatch_issue",0])
        self.summary_rpt.append(["records_skipped_due_to_issue",0])
        self.summary_rpt.append(["number_of_records_truncated",0])
        self.summary_rpt.append(["number_of_geometry_duplicate",0])
        self.summary_rpt.append(["is_any_val_truncated",0])
        self.summary_rpt.append(["number_of_values_truncated",0])
        logging.info("reachied at init in Summary")

    def CreateSummaryExcel(self,process_start_time, process_end_time
                ,source_file_gdb,source_table,cdif_zip_file,iqgeo_object_name
                ,filter_condition, total_records_selected, total_records_processed, records_skipped_due_to_issue
                , records_skipped_due_to_parent_data_mismatch_issue, number_of_records_truncated,
                number_of_values_truncated, number_of_geometry_duplicate,field_ary ):
        try:
            df_xl1 = pd.DataFrame(self.string_truncate_object, columns=['Object ID','Field Name', 'Original String', 'Truncated String'])
            df_xl2 = pd.DataFrame(self.duplicate_geom, columns=['Object ID','Geom'])
            df_xl3 = pd.DataFrame(self.bypassed_data, columns=['Object ID','Bypassed for Field','Field Value'])
            
            
            excel_file_path = self.report_file_path + "\\SummaryReport_"+iqgeo_object_name.upper()+"_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".xlsx"
            

            with pd.ExcelWriter(excel_file_path, engine='xlsxwriter') as writer:
                df_xl1.to_excel(writer, sheet_name='TruncatedValues', index=False)
                df_xl2.to_excel(writer, sheet_name='DuplicateGeom', index=False)
                df_xl3.to_excel(writer, sheet_name='OutsideDomain', index=False)
            
            
            
            wb = load_workbook(excel_file_path)
            # Create a new sheet
            ws_openpyxl = wb.create_sheet('Summary',0)

            # Add data to the new sheet using openpyxl
            ws_openpyxl['A1'] = 'NE to IQGeo Object Migration Summary Report : ' + iqgeo_object_name
            ws_openpyxl.merge_cells('A1:D1')
            ws_openpyxl['A1'].font = Font(name='Arial', size=14, bold=True, color="FF0000") 
            ws_openpyxl['A1'].alignment = Alignment(horizontal='center', vertical='center')
            ws_openpyxl['A2'] = 'Start Time'
            ws_openpyxl['A3'] = "End Time"
            ws_openpyxl['A4'] = "Total Time Taken (min:sec)"
            ws_openpyxl['A5'] = "NE Source FileGDB"
            ws_openpyxl['A6'] = "NE Source Feature Layer"
            ws_openpyxl['A7'] = "Generated CDIF File"
            ws_openpyxl['A8'] = "IQGeo Object Name"
            ws_openpyxl['A9'] = "Condition Used to Select NE Data"
            ws_openpyxl['A10'] = "Total Records selected as per Condition"
            ws_openpyxl['A11'] = "Total Records Processed"
            ws_openpyxl['A12'] ="Records Skipped due to value / data type issue"
            ws_openpyxl['A13'] ="Records Skipped due to reference /parent data missing reason"
            ws_openpyxl['A14'] ="Number of Records where data trucated due to shorter length"
            ws_openpyxl['A15'] ="Number of values where data trucated due to shorter length"
            ws_openpyxl['A16'] ="Number of Duplicate Geometires"
            
            m, s = divmod(process_end_time-process_start_time, 60)

            ws_openpyxl['B2'] = datetime.fromtimestamp(process_start_time).strftime("%d-%b-%Y %H:%M:%S")
            ws_openpyxl['B3'] = datetime.fromtimestamp(process_end_time).strftime("%d-%b-%Y %H:%M:%S")
            ws_openpyxl['B4'] = str(int(m)) + ":" + str(int(s))
            ws_openpyxl['B5'] = source_file_gdb
            ws_openpyxl['B6'] = source_table
            ws_openpyxl['B7'] = cdif_zip_file
            ws_openpyxl['B8'] = iqgeo_object_name
            ws_openpyxl['B9'] = filter_condition
            ws_openpyxl['B10'] = total_records_selected
            ws_openpyxl['B11'] = total_records_processed
            ws_openpyxl['B12'] = records_skipped_due_to_issue
            ws_openpyxl['B13'] = records_skipped_due_to_parent_data_mismatch_issue
            ws_openpyxl['B14'] = number_of_records_truncated
            ws_openpyxl['B15'] =number_of_values_truncated
            ws_openpyxl['B16'] =number_of_geometry_duplicate

            

            ws_openpyxl.merge_cells('B2:D2')
            ws_openpyxl.merge_cells('B3:D3')
            ws_openpyxl.merge_cells('B4:D4')
            ws_openpyxl.merge_cells('B5:D5')
            ws_openpyxl.merge_cells('B6:D6')
            ws_openpyxl.merge_cells('B7:D7')
            ws_openpyxl.merge_cells('B8:D8')
            ws_openpyxl.merge_cells('B9:D9')
            ws_openpyxl.merge_cells('B10:D10')
            ws_openpyxl.merge_cells('B11:D11')
            ws_openpyxl.merge_cells('B12:D12')
            ws_openpyxl.merge_cells('B13:D13')
            ws_openpyxl.merge_cells('B14:D14')
            ws_openpyxl.merge_cells('B15:D15')
            ws_openpyxl.merge_cells('B16:D16')
            
            ws_openpyxl['A18'] ="Field Wise Abstract"
            ws_openpyxl.merge_cells('A18:D18')
            ws_openpyxl['A18'].font = Font(bold=True)
            ws_openpyxl['A18'].alignment  = Alignment(horizontal='center', vertical='center')

            ws_openpyxl['A19'] = 'Field Name'
            ws_openpyxl['B19'] = 'Mandatory ?'
            ws_openpyxl['C19'] = 'NULL Value Found'
            ws_openpyxl['D19'] = 'Outside Domain/Pick List Value'
            ws_openpyxl['E19'] = 'Data Truncated'
            


            ws_openpyxl.column_dimensions['A'].width = 60
            ws_openpyxl.column_dimensions['B'].width = 17
            ws_openpyxl.column_dimensions['C'].width = 30
            ws_openpyxl.column_dimensions['D'].width = 17
            ws_openpyxl.column_dimensions['E'].width = 17
            
            rwno=20
            for fld in field_ary:
                ws_openpyxl['A'+str(rwno)] = fld[0]
                ws_openpyxl['B'+str(rwno)] = fld[4]
                ws_openpyxl['C'+str(rwno)] = fld[1]
                ws_openpyxl['D'+str(rwno)] = fld[2]
                ws_openpyxl['E'+str(rwno)] = fld[3]
                if  fld[4].lower()=="yes":
                    if int(fld[1])>0:
                        ws_openpyxl['C'+str(rwno)].font = Font(bold=True, color="FF0000") 
                
                if int(fld[2])>0:
                        ws_openpyxl['D'+str(rwno)].fill = PatternFill(start_color="FFFFCC00", end_color="FFFFCC00", fill_type="solid") # Goldenrod yellow

                if int(fld[3])>0:
                        ws_openpyxl['E'+str(rwno)].fill = PatternFill(start_color="ff6900", end_color="ff6900", fill_type="solid") 

                rwno+=1
            # Save the modified workbook
            wb.active = ws_openpyxl
            wb.save(excel_file_path)
        except Exception as e:
            print(f"Error occured during domain value check '{str(e)}' for summary report creation at path   '{excel_file_path}'  ")
            logging.error(f"Error occured during domain value check '{str(e)}' for summary report creation at path   '{excel_file_path}'  ")