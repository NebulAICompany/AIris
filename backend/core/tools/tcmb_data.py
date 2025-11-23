import os
from typing import Dict, Any, List
from evds import evdsAPI
import pandas as pd
from agents import function_tool
from backend.shared.logger import get_logger

logger = get_logger("TCMB_TOOLS")

# Main categories list - predefined to avoid repeated API calls
MAIN_CATEGORIES = [
    (1, 'PİYASA VERİLERİ (TCMB)'),
    (2, 'KURLAR (TCMB)'),
    (3, 'FAİZ VE KÂR PAYI İSTATİSTİKLERİ (TCMB)'),
    (4, 'AYLIK PARA VE BANKA İSTATİSTİKLERİ (TCMB)'),
    (5, 'MENKUL KIYMET İSTATİSTİKLERİ (TCMB)'),
    (6, 'TÜRKİYE BRÜT DIŞ BORÇ STOKU (HMB)'),
    (7, 'ZORUNLU KARŞILIKLARA TABİ MEVDUAT VE KATILIM FONLARI (TCMB)'),
    (9, 'BANKA DIŞI FİNANSAL KURULUŞLAR İSTATİSTİKLERİ (TCMB)'),
    (10, 'BANKA KREDİLERİ EĞİLİM ANKETİ (TCMB)'),
    (11, 'BANKA VE KREDİ KARTI İSTATİSTİKLERİ (TCMB, BKM)'),
    (12, 'FİNANSAL HİZMETLER ANKETİ (TCMB)'),
    (13, 'MERKEZ BANKASI BİLANÇO VERİLERİ (TCMB)'),
    (14, 'FİYAT ENDEKSLERİ'),
    (15, 'İKTİSADİ YÖNELİM ANKETİ (TCMB)'),
    (16, 'BİLEŞİK ÖNCÜ GÖSTERGELER ENDEKSİ (TCMB)'),
    (18, 'ULUSLARARASI YATIRIM POZİSYONU (TCMB)'),
    (19, 'DIŞ TİCARET İSTATİSTİKLERİ (TÜİK)'),
    (20, 'KAMU MALİ İSTATİSTİKLERİ (HMB)'),
    (21, 'ÜRETİME İLİŞKİN DİĞER VERİLER'),
    (22, 'ÖDEME SİSTEMLERİ İSTATİSTİKLERİ (TCMB)'),
    (23, 'İŞGÜCÜ İSTATİSTİKLERİ (TÜİK)'),
    (24, 'ULUSLARARASI İSTATİSTİKLER'),
    (25, 'ALTIN İSTATİSTİKLERİ'),
    (26, 'KONUT FİYAT ENDEKSİ (TCMB)'),
    (27, 'FİNANSAL HESAPLAR (TCMB)'),
    (28, 'KONUT VE İNŞAAT İSTATİSTİKLERİ (TÜİK)'),
    (29, 'DIŞ TİCARET ENDEKSLERİ (TÜİK)'),
    (30, 'DIŞ TİCARET NAKLİYE ARAÇLARI İSTATİSTİKLERİ (UND)'),
    (31, 'DİĞER FİNANSAL VERİLER'),
    (32, 'FİNANSAL KESİM DIŞINDAKİ FİRMALARIN DÖVİZ VARLIK VE YÜKÜMLÜLÜKLERİ (TCMB)'),
    (33, 'HAFTALIK PARA VE BANKA İSTATİSTİKLERİ (TCMB)'),
    (34, 'İMALAT SANAYİ KAPASİTE KULLANIM ORANI (TCMB)'),
    (35, 'KISA VADELİ DIŞ BORÇ İSTATİSTİKLERİ (TCMB)'),
    (36, 'ÖDEMELER DENGESİ İSTATİSTİKLERİ (TCMB)'),
    (37, 'ÖZEL SEKTÖRÜN YURT DIŞINDAN SAĞLADIĞI KREDİ BORCU İSTATİSTİKLERİ (TCMB)'),
    (38, 'PİYASA KATILIMCILARI ANKETİ (TCMB)'),
    (39, 'TEDAVÜLDEKİ BANKNOTLAR (TCMB)'),
    (40, 'TÜKETİCİ EĞİLİM ANKETİ (TÜİK, TCMB)'),
    (41, 'ULUSAL HESAPLAR (TÜİK)'),
    (42, 'ULUSLARARASI REZERVLER VE DÖVİZ LİKİDİTESİ (TCMB)'),
    (44, 'SEKTÖR BİLANÇOLARI (2023 - 2024)'),
    (45, 'TİCARİ GAYRİMENKUL FİYAT ENDEKSİ (TCMB)'),
    (46, 'SEKTÖREL ENFLASYON BEKLENTİLERİ (TCMB, TÜİK)'),
    (47, 'SEKTÖR BİLANÇOLARI (2009 - 2023)')
]

# Initialize EVDS API client
def _get_evds_client():
    """Get EVDS API client instance."""
    api_key = os.getenv("TCMB_API_KEY")
    if not api_key:
        raise ValueError("TCMB_API_KEY environment variable is not set")
    return evdsAPI(api_key)


@function_tool()
def get_tcmb_subcategories(category_id: int) -> Dict[str, Any]:
    """
    Get subcategories for a given TCMB main category ID.
    
    Args:
        category_id: The main category ID (e.g., 1 for 'PİYASA VERİLERİ (TCMB)')
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - subcategories (List[Dict]): List of subcategories with DATAGROUP_CODE and DATAGROUP_NAME
            - count (int): Number of subcategories found
            - category_id (int): The queried category ID
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        logger.info(f"Fetching subcategories for category_id: {category_id}")
        
        # Get EVDS client
        evds = _get_evds_client()
        
        # Get subcategories
        subcategories_df = evds.get_sub_categories(category_id)
        
        # Convert DataFrame to list of dictionaries
        if isinstance(subcategories_df, pd.DataFrame) and not subcategories_df.empty:
            subcategories_list = []
            for _, row in subcategories_df.iterrows():
                subcategories_list.append({
                    "DATAGROUP_CODE": row.get("DATAGROUP_CODE", ""),
                    "DATAGROUP_NAME": row.get("DATAGROUP_NAME", "")
                })
            
            logger.info(f"Successfully fetched {len(subcategories_list)} subcategories for category_id: {category_id}")
            return {
                "success": True,
                "subcategories": subcategories_list,
                "count": len(subcategories_list),
                "category_id": category_id,
                "message": f"Successfully retrieved {len(subcategories_list)} subcategories"
            }
        else:
            return {
                "success": False,
                "error": f"No subcategories found for category_id: {category_id}"
            }
            
    except Exception as e:
        error_msg = f"Error fetching subcategories for category_id {category_id}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }


@function_tool()
def get_tcmb_series(datagroup_code: str) -> Dict[str, Any]:
    """
    Get series information for a given TCMB datagroup code.
    
    Args:
        datagroup_code: The datagroup code (e.g., 'bie_sekbil1122')
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - series (List[Dict]): List of series with SERIE_CODE, SERIE_NAME, and START_DATE
            - count (int): Number of series found
            - datagroup_code (str): The queried datagroup code
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        logger.info(f"Fetching series for datagroup_code: {datagroup_code}")
        
        # Get EVDS client
        evds = _get_evds_client()
        
        # Get series
        series_df = evds.get_series(datagroup_code)
        
        # Convert DataFrame to list of dictionaries
        if isinstance(series_df, pd.DataFrame) and not series_df.empty:
            series_list = []
            for _, row in series_df.iterrows():
                series_list.append({
                    "SERIE_CODE": row.get("SERIE_CODE", ""),
                    "SERIE_NAME": row.get("SERIE_NAME", ""),
                    "START_DATE": row.get("START_DATE", "")
                })
            
            logger.info(f"Successfully fetched {len(series_list)} series for datagroup_code: {datagroup_code}")
            return {
                "success": True,
                "series": series_list,
                "count": len(series_list),
                "datagroup_code": datagroup_code,
                "message": f"Successfully retrieved {len(series_list)} series"
            }
        else:
            return {
                "success": False,
                "error": f"No series found for datagroup_code: {datagroup_code}"
            }
            
    except Exception as e:
        error_msg = f"Error fetching series for datagroup_code {datagroup_code}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }


@function_tool()
def get_tcmb_data(
    serie_codes: List[str],
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    Get actual data for given TCMB serie codes within a date range.
    
    Args:
        serie_codes: List of serie codes (e.g., ['TP.SEKBILTGA.A'])
        start_date: Start date in format 'DD-MM-YYYY' (e.g., '01-01-2019')
        end_date: End date in format 'DD-MM-YYYY' (e.g., '01-01-2020')
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if operation succeeded, False otherwise
            - data (Dict): Data in JSON format with dates as keys
            - serie_codes (List[str]): The queried serie codes
            - start_date (str): Start date of the query
            - end_date (str): End date of the query
            - rows (int): Number of data rows returned
            - message (str): Success message (if successful)
            - error (str): Error message (if failed)
    """
    try:
        logger.info(f"Fetching data for serie_codes: {serie_codes}, date range: {start_date} to {end_date}")
        
        # Get EVDS client
        evds = _get_evds_client()
        
        # Get data
        data_df = evds.get_data(serie_codes, startdate=start_date, enddate=end_date)
        
        # Convert DataFrame to dictionary format
        if isinstance(data_df, pd.DataFrame) and not data_df.empty:
            # Convert DataFrame to dict with 'records' orientation for better readability
            data_dict = data_df.to_dict(orient='records')
            
            logger.info(f"Successfully fetched {len(data_dict)} rows of data for serie_codes: {serie_codes}")
            return {
                "success": True,
                "data": data_dict,
                "serie_codes": serie_codes,
                "start_date": start_date,
                "end_date": end_date,
                "rows": len(data_dict),
                "message": f"Successfully retrieved {len(data_dict)} rows of data"
            }
        else:
            return {
                "success": False,
                "error": f"No data found for serie_codes: {serie_codes} in date range {start_date} to {end_date}"
            }
            
    except Exception as e:
        error_msg = f"Error fetching data for serie_codes {serie_codes}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }