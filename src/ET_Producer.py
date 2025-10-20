import os
import sys
import magic
import shutil
import hashlib
import tkinter
import threading
import traceback
import customtkinter
import xml.etree.ElementTree as ET
from uuid import uuid1
from datetime import datetime
from subprocess import run, DEVNULL
from tkinter import messagebox, filedialog, Label, StringVar, Menu

MUNICIPALITY_LIST = sorted(["5041 Snåsa Kommune", "5057 Ørland Kommune", "5059 Orkland Kommune", "5034 Meråker Kommune", "5037 Levanger Kommune", "5025 Røros Kommune", "5016 Agdenes Kommune", "5012 Snillfjord Kommune", "5036 Frosta Kommune", "5023 Meldal Kommune", "5044 Namsskogan Kommune", "5043 Røyrvik Kommune", "5011 Hemne Kommune", "5032 Selbu Kommune", "5035 Stjørdal Kommune", "5046 Høylandet Kommune", "5042 Lierne Kommune", "5045 Grong Kommune","5049 Flatanger Kommune","5014 Frøya Kommune","5055 Heim Kommune","5013 Hitra Kommune","5026 Holtålen Kommune","5053 Inderøy Kommune","5054 Indre Fosen Kommune","5031 Malvik Kommune","5028 Melhus Kommune","5027 Midtre Gauldal Kommune","5005 Namsos Kommune","5060 Nærøysund Kommune","5021 Oppdal Kommune","3430 Os Kommune","5047 Overhalla Kommune","5020 Osen Kommune","5022 Rennebu Kommune","5029 Skaun Kommune","5006 Steinkjer Kommune","5033 Tydal Kommune","5038 Verdal Kommune","5058 Åfjord Kommune"], key=lambda x: x.split(" ")[1])
SYSTEM_LIST = sorted(["ESA", "Visma Velferd", "Visma Familia", "Visma HsPro", "WinMed Helse", "Ephorte", "Visma Flyt Skole", "Visma Profil", "SystemX", "P360", "Digora", "Oppad", "CGM Helsestasjon", "Visma Flyt Sampro", "Gerica", "Socio"])
USERNAME = "admin"

def browse_files(label: Label):
    """Browse computer for folder selection"""
    file = filedialog.askdirectory(initialdir="./", title="Choose a folder whose content should be packaged")
    label.configure(text=file)

def import_metadata(path: str):
    """Import metadata from METS XML file using iterative parsing for large files"""
    # Extended patterns to match various METS formats
    compare_dict = {
        frozenset(["ORGANIZATION","ARCHIVIST"]): [TEXT_LIST[3]], 
        frozenset(["OTHER","SOFTWARE","ARCHIVIST"]): [TEXT_LIST[0],TEXT_LIST[1],TEXT_LIST[5]], 
        frozenset(["ORGANIZATION","OTHER","PRODUCER"]): [TEXT_LIST[7]], 
        frozenset(["INDIVIDUAL","OTHER","PRODUCER"]): [TEXT_LIST[8]], 
        frozenset(["OTHER","SOFTWARE","OTHER","PRODUCER"]): [TEXT_LIST[9]], 
        frozenset(["ORGANIZATION","OTHER","SUBMITTER"]): [TEXT_LIST[12]], 
        frozenset(["INDIVIDUAL","OTHER","SUBMITTER"]): [TEXT_LIST[13]], 
        frozenset(["ORGANIZATION","IPOWNER"]): [TEXT_LIST[6]],
        frozenset(["INDIVIDUAL","IPOWNER"]): [TEXT_LIST[6]],
        frozenset(["STARTDATE"]): [TEXT_LIST[10]], 
        frozenset(["ENDDATE"]): [TEXT_LIST[11]],
        frozenset(["ORGANIZATION","OTHER","OTHERROLE","PRODUCER"]): [TEXT_LIST[7]],
        frozenset(["INDIVIDUAL","OTHER","OTHERROLE","PRODUCER"]): [TEXT_LIST[8]],
        frozenset(["OTHER","SOFTWARE","OTHER","OTHERROLE","PRODUCER"]): [TEXT_LIST[9]],
        frozenset(["ORGANIZATION","OTHER","OTHERROLE","SUBMITTER"]): [TEXT_LIST[12]],
        frozenset(["INDIVIDUAL","OTHER","OTHERROLE","SUBMITTER"]): [TEXT_LIST[13]],
        frozenset(["ORGANIZATION","CREATOR"]): [TEXT_LIST[14]],
        frozenset(["INDIVIDUAL","CREATOR"]): [TEXT_LIST[14]],
        frozenset(["OTHER","SOFTWARE","CREATOR","OTHERTYPE"]): [TEXT_LIST[9]],
        frozenset(["ORGANIZATION","PRESERVATION"]): [TEXT_LIST[15]],
    }
    
    if not path:
        return
        
    try:
        file_size = os.path.getsize(path.name)
        log(f"Importing metadata from {os.path.basename(path.name)} ({file_size / (1024*1024):.1f}MB)...")
        
        found_elements = []
        imported_count = 0
        in_mets_hdr = False
        found_mets_hdr = False
        
        context = ET.iterparse(path.name, events=("start", "end"))
        
        for event, elem in context:
            try:
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                
                if event == "start" and tag.lower() == "metshdr":
                    in_mets_hdr = True
                    found_mets_hdr = True
                    log("  Found metsHdr - extracting metadata...")
                    continue
                
                if event == "end" and tag.lower() == "metshdr":
                    in_mets_hdr = False
                    break
                
                if event == "end" and in_mets_hdr:
                    elem_info = f"Tag: {tag}"
                    if elem.attrib:
                        elem_info += f", Attributes: {dict(elem.attrib)}"
                    if elem.text and elem.text.strip():
                        elem_info += f", Text: {elem.text.strip()[:50]}"
                    found_elements.append(elem_info)
                    
                    if elem.attrib:
                        attrib_set = frozenset(elem.attrib.values())
                        
                        if tag.lower() == "agent" and len(list(elem)) > 0:
                            if attrib_set in compare_dict:
                                for child in elem:
                                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                                    if child_tag.lower() == "name" and child.text:
                                        if compare_dict[attrib_set]:
                                            field = compare_dict[attrib_set].pop(0)
                                            field.set(child.text.strip())
                                            imported_count += 1
                                            log(f"  ✓ Imported: {child.text.strip()}")
                        
                        elif tag.lower() == "altrecordid" and elem.text:
                            if attrib_set in compare_dict and compare_dict[attrib_set]:
                                field = compare_dict[attrib_set][0]
                                field.set(elem.text.strip())
                                imported_count += 1
                                log(f"  ✓ Imported: {elem.text.strip()}")
                    
                    elem.clear()
            except Exception as e:
                log(f"  ⚠ Error processing element: {str(e)}")
                continue
        
        log(f"Import complete: {imported_count} field(s) filled")
        
        if imported_count > 0:
            messagebox.showinfo("Success", f"Metadata imported!\n{imported_count} field(s) filled.")
        else:
            messagebox.showinfo("Info", "No matching fields found.\nYou can fill the form manually.")
            
    except Exception as e:
        log(f"⚠ Import error: {str(e)}")
        messagebox.showinfo("Info", "Import completed with issues.\nYou can fill the form manually.")

def gather_file_info(directory: str, prefix: str) -> dict:
    """Get SHA-256 hash, mimetype, filesize and creation date for all files"""
    log(f"Gathering checksums from: {directory}")
    info_dict = {}
    file_count = 0
    error_count = 0
    
    # Count total files
    total_files = sum(len(files) for _, _, files in os.walk(directory))
    log(f"  Found {total_files} files to process")
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_count += 1
            file_path = os.path.join(root, file)
            
            try:
                # Log progress every 50 files
                if file_count % 50 == 0 or file_count == total_files:
                    log(f"  Progress: {file_count}/{total_files} files")
                
                sha = hashlib.sha256()
                with open(file_path, "rb") as f:
                    tmp_data = f.read(4000000)
                    tmp_magic = magic.from_buffer(tmp_data, mime=True)
                    while tmp_data:
                        sha.update(tmp_data)
                        tmp_data = f.read(4000000)
                
                relative_path = os.path.relpath(root, directory).replace(os.sep, "/")
                if relative_path == ".":
                    relative_path = ""
                else:
                    relative_path = "/" + relative_path
                
                info_dict[f'{prefix}{relative_path}/{file}'] = [
                    sha.hexdigest(), 
                    tmp_magic, 
                    os.stat(file_path).st_size, 
                    datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%dT%H:%M:%S+02:00")
                ]
                
            except Exception as e:
                error_count += 1
                log(f"  ⚠ Error processing {file}: {str(e)}")
                continue
    
    log(f"  ✓ Processed: {file_count - error_count}/{total_files} files")
    if error_count > 0:
        log(f"  ⚠ Skipped: {error_count} files due to errors")
    
    return info_dict

def pack_sip(sip_tarfile: str, id: str, content_path: str):
    """Package the SIP into a tar archive using native Linux tar command"""
    log("Packaging SIP into tar archive...")
    
    tar_file = f"{sip_tarfile}.tar"
    sip_dir = os.path.dirname(sip_tarfile)
    sip_basename = os.path.basename(sip_tarfile)
    content_basename = os.path.basename(content_path)
    
    # Create tar with SIP directory
    log("  Creating tar archive...")
    run(['tar', '-cf', tar_file, '-C', sip_dir, sip_basename], stdout=DEVNULL, stderr=DEVNULL, check=True)
    
    # Append content
    log("  Adding content to archive...")
    run(['tar', '-rf', tar_file, '-C', os.path.dirname(content_path), content_basename], stdout=DEVNULL, stderr=DEVNULL, check=True)
    
    # Extract, reorganize, and repackage
    log("  Reorganizing archive structure...")
    temp_extract = f"{sip_dir}/temp_extract_{uuid1()}"
    os.makedirs(temp_extract, exist_ok=True)
    
    try:
        run(['tar', '-xf', tar_file, '-C', temp_extract], stdout=DEVNULL, stderr=DEVNULL, check=True)
        
        # Move content to correct location
        content_dest = os.path.join(temp_extract, sip_basename, 'content')
        content_src = os.path.join(temp_extract, content_basename)
        
        if os.path.exists(content_src):
            shutil.move(content_src, content_dest)
        
        # Recreate tar with correct structure
        os.remove(tar_file)
        run(['tar', '-cf', tar_file, '-C', temp_extract, sip_basename], stdout=DEVNULL, stderr=DEVNULL, check=True)
        
        # Clean up original SIP directory
        original_sip = os.path.join(sip_dir, sip_basename)
        if os.path.exists(original_sip):
            shutil.rmtree(original_sip)
            
    finally:
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
    
    log("  ✓ Packaging complete")

def configure_sip_log(log_path: str, id: str, create_date: str):
    """Configure SIP log.xml"""
    with open(log_path, "w", encoding="utf-8") as fo:
        string_log = f'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<premis:premis xmlns:premis="http://arkivverket.no/standarder/PREMIS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://arkivverket.no/standarder/PREMIS http://schema.arkivverket.no/PREMIS/v2.0/DIAS_PREMIS.xsd" version="2.0">\n  <premis:object xsi:type="premis:file">\n    <premis:objectIdentifier>\n      <premis:objectIdentifierType>NO/RA</premis:objectIdentifierType>\n      <premis:objectIdentifierValue>{id}</premis:objectIdentifierValue>\n    </premis:objectIdentifier>\n    <premis:preservationLevel>\n      <premis:preservationLevelValue>full</premis:preservationLevelValue>\n    </premis:preservationLevel>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>aic_object</premis:significantPropertiesType>\n      <premis:significantPropertiesValue></premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>createdate</premis:significantPropertiesType>\n      <premis:significantPropertiesValue>{create_date}</premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>archivist_organization</premis:significantPropertiesType>\n      <premis:significantPropertiesValue>{archivist_org_combo.get()}</premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>label</premis:significantPropertiesType>\n      <premis:significantPropertiesValue>{label_entry.get()}</premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>iptype</premis:significantPropertiesType>\n      <premis:significantPropertiesValue>SIP</premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:objectCharacteristics>\n      <premis:compositionLevel>0</premis:compositionLevel>\n      <premis:format>\n        <premis:formatDesignation>\n          <premis:formatName>tar</premis:formatName>\n        </premis:formatDesignation>\n      </premis:format>\n    </premis:objectCharacteristics>\n    <premis:storage>\n      <premis:storageMedium>Preservation platform ESSArch</premis:storageMedium>\n    </premis:storage>\n    <premis:relationship>\n      <premis:relationshipType>structural</premis:relationshipType>\n      <premis:relationshipSubType>is part of</premis:relationshipSubType>\n      <premis:relatedObjectIdentification>\n        <premis:relatedObjectIdentifierType>NO/RA</premis:relatedObjectIdentifierType>\n        <premis:relatedObjectIdentifierValue></premis:relatedObjectIdentifierValue>\n      </premis:relatedObjectIdentification>\n    </premis:relationship>\n  </premis:object>\n  <premis:event>\n    <premis:eventIdentifier>\n      <premis:eventIdentifierType>NO/RA</premis:eventIdentifierType>\n      <premis:eventIdentifierValue>{uuid1()}</premis:eventIdentifierValue>\n    </premis:eventIdentifier>\n    <premis:eventType>10000</premis:eventType>\n    <premis:eventDateTime>{create_date}</premis:eventDateTime>\n    <premis:eventDetail>Log circular created</premis:eventDetail>\n    <premis:eventOutcomeInformation>\n      <premis:eventOutcome>0</premis:eventOutcome>\n      <premis:eventOutcomeDetail>\n        <premis:eventOutcomeDetailNote>Success to create logfile</premis:eventOutcomeDetailNote>\n      </premis:eventOutcomeDetail>\n    </premis:eventOutcomeInformation>\n    <premis:linkingAgentIdentifier>\n      <premis:linkingAgentIdentifierType>NO/RA</premis:linkingAgentIdentifierType>\n      <premis:linkingAgentIdentifierValue>{USERNAME}</premis:linkingAgentIdentifierValue>\n    </premis:linkingAgentIdentifier>\n    <premis:linkingObjectIdentifier>\n      <premis:linkingObjectIdentifierType>NO/RA</premis:linkingObjectIdentifierType>\n      <premis:linkingObjectIdentifierValue>{id}</premis:linkingObjectIdentifierValue>\n    </premis:linkingObjectIdentifier>\n  </premis:event>\n</premis:premis>'
        fo.write(string_log)

def configure_sip_premis(premis_path: str, id: str, info_dict: dict):
    """Configure SIP premis.xml"""
    start_premis = f'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n <premis:premis xmlns:premis="http://arkivverket.no/standarder/PREMIS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://arkivverket.no/standarder/PREMIS http://schema.arkivverket.no/PREMIS/v2.0/DIAS_PREMIS.xsd" version="2.0">\n  <premis:object xsi:type="premis:file">\n    <premis:objectIdentifier>\n      <premis:objectIdentifierType>NO/RA</premis:objectIdentifierType>\n      <premis:objectIdentifierValue>{id}</premis:objectIdentifierValue>\n    </premis:objectIdentifier>\n    <premis:preservationLevel>\n      <premis:preservationLevelValue>full</premis:preservationLevelValue>\n    </premis:preservationLevel>\n    <premis:objectCharacteristics>\n      <premis:compositionLevel>0</premis:compositionLevel>\n      <premis:format>\n        <premis:formatDesignation>\n          <premis:formatName>tar</premis:formatName>\n        </premis:formatDesignation>\n      </premis:format>\n    </premis:objectCharacteristics>\n    <premis:storage>\n      <premis:storageMedium>ESSArch Tools</premis:storageMedium>\n    </premis:storage>\n  </premis:object>\n'
    end_premis = f'  <premis:agent>\n    <premis:agentIdentifier>\n      <premis:agentIdentifierType>NO/RA</premis:agentIdentifierType>\n      <premis:agentIdentifierValue>ESSArch</premis:agentIdentifierValue>\n    </premis:agentIdentifier>\n    <premis:agentName>ESSArch Tools</premis:agentName>\n    <premis:agentType>software</premis:agentType>\n  </premis:agent>\n</premis:premis>'
    
    with open(premis_path, "w", encoding="utf-8") as fo:
        fo.write(start_premis)
        for path, info in info_dict.items():
            if path != f'{id}/mets.xml' and path != f'{id}/administrative_metadata/premis.xml':
                fill_premis = f'  <premis:object xsi:type="premis:file">\n    <premis:objectIdentifier>\n      <premis:objectIdentifierType>NO/RA</premis:objectIdentifierType>\n      <premis:objectIdentifierValue>{path}</premis:objectIdentifierValue>\n    </premis:objectIdentifier>\n    <premis:objectCharacteristics>\n      <premis:compositionLevel>0</premis:compositionLevel>\n      <premis:fixity>\n        <premis:messageDigestAlgorithm>SHA-256</premis:messageDigestAlgorithm>\n        <premis:messageDigest>{info[0]}</premis:messageDigest>\n        <premis:messageDigestOriginator>ESSArch</premis:messageDigestOriginator>\n      </premis:fixity>\n      <premis:size>{info[2]}</premis:size>\n      <premis:format>\n        <premis:formatDesignation>\n          <premis:formatName>{os.path.splitext(path)[1][1:]}</premis:formatName>\n        </premis:formatDesignation>\n      </premis:format>\n    </premis:objectCharacteristics>\n    <premis:storage>\n      <premis:contentLocation>\n        <premis:contentLocationType>SIP</premis:contentLocationType>\n        <premis:contentLocationValue>{id}</premis:contentLocationValue>\n      </premis:contentLocation>\n    </premis:storage>\n    <premis:relationship>\n      <premis:relationshipType>structural</premis:relationshipType>\n      <premis:relationshipSubType>is part of</premis:relationshipSubType>\n      <premis:relatedObjectIdentification>\n        <premis:relatedObjectIdentifierType>NO/RA</premis:relatedObjectIdentifierType>\n        <premis:relatedObjectIdentifierValue>{id}</premis:relatedObjectIdentifierValue>\n      </premis:relatedObjectIdentification>\n    </premis:relationship>\n  </premis:object>\n'
                fo.write(fill_premis)
        fo.write(end_premis)

def configure_sip_mets(mets_path: str, id: str, creation_date: str, premis_path: str, info_dict: dict):
    """Configure SIP mets.xml"""
    with open(mets_path, "w", encoding="utf-8") as fo:
        sha = hashlib.sha256()
        with open(premis_path, "rb") as f:
            while True:
                tmp_data = f.read(4000000)
                if not tmp_data:
                    break
                sha.update(tmp_data)
        
        id_list = [f'ID{uuid1()}']
        start_mets = f'<?xml version="1.0" encoding="UTF-8"?>\n<mets:mets xmlns:mets="http://www.loc.gov/METS/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/METS/ http://schema.arkivverket.no/METS/mets.xsd" PROFILE="http://xml.ra.se/METS/RA_METS_eARD.xml" LABEL="{label_entry.get()}" TYPE="SIP" ID="ID{uuid1()}" OBJID="UUID:{id}">\n    <mets:metsHdr CREATEDATE="{creation_date}" RECORDSTATUS="NEW">\n        <mets:agent TYPE="ORGANIZATION" ROLE="ARCHIVIST">\n            <mets:name>{archivist_org_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="ARCHIVIST">\n            <mets:name>{system_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="ARCHIVIST">\n            <mets:name>{system_ver_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="ARCHIVIST">\n            <mets:name>{type_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="CREATOR">\n            <mets:name>{creator_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="OTHER" OTHERROLE="PRODUCER">\n            <mets:name>{producer_org_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="INDIVIDUAL" ROLE="OTHER" OTHERROLE="PRODUCER">\n            <mets:name>{producer_pers_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="OTHER" OTHERROLE="PRODUCER">\n            <mets:name>{producer_software_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="OTHER" OTHERROLE="SUBMITTER">\n            <mets:name>{submitter_org_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="INDIVIDUAL" ROLE="OTHER" OTHERROLE="SUBMITTER">\n            <mets:name>{submitter_pers_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="IPOWNER">\n            <mets:name>{owner_org_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="PRESERVATION">\n            <mets:name>{preserver_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:altRecordID TYPE="SUBMISSIONAGREEMENT">{submission_entry.get()}</mets:altRecordID>\n        <mets:altRecordID TYPE="STARTDATE">{period_start_entry.get()}</mets:altRecordID>\n        <mets:altRecordID TYPE="ENDDATE">{period_end_entry.get()}</mets:altRecordID>\n        <mets:metsDocumentID>mets.xml</mets:metsDocumentID>\n    </mets:metsHdr>\n    <mets:amdSec ID="amdSec001">\n        <mets:digiprovMD ID="digiprovMD001">\n            <mets:mdRef MIMETYPE="text/xml" CHECKSUMTYPE="SHA-256" CHECKSUM="{sha.hexdigest()}" MDTYPE="PREMIS" xlink:href="file:administrative_metadata/premis.xml" LOCTYPE="URL" CREATED="{datetime.fromtimestamp(os.path.getmtime(premis_path)).strftime("%Y-%m-%dT%H:%M:%S+02:00")}" xlink:type="simple" ID="{id_list[-1]}" SIZE="{os.stat(premis_path).st_size}"/>\n        </mets:digiprovMD>\n    </mets:amdSec>\n    <mets:fileSec>\n        <mets:fileGrp ID="fgrp001" USE="FILES">\n'
        end_mets = f'            </mets:div>\n        </mets:div>\n    </mets:structMap>\n</mets:mets>'
        
        fo.write(start_mets)
        for path, info in info_dict.items():
            tmp_path = 'file:' + path.removeprefix(f'{id}/')
            if tmp_path != "file:administrative_metadata/premis.xml" and tmp_path != "file:mets.xml":
                id_list.append(f'ID{uuid1()}')
                fill_mets = f'            <mets:file MIMETYPE="{info[1]}" CHECKSUMTYPE="SHA-256" CREATED="{info[3]}" CHECKSUM="{info[0]}" USE="Datafile" ID="{id_list[-1]}" SIZE="{info[2]}">\n                <mets:FLocat xlink:href="{tmp_path}" LOCTYPE="URL" xlink:type="simple"/>\n            </mets:file>\n'
                fo.write(fill_mets)
        
        fill_mets = f'        </mets:fileGrp>\n    </mets:fileSec>\n    <mets:structMap>\n        <mets:div LABEL="Package">\n            <mets:div ADMID="amdSec001" LABEL="Content Description">\n                <mets:fptr FILEID="{id_list.pop(0)}"/>\n            </mets:div>\n            <mets:div ADMID="amdSec001" LABEL="Datafiles">\n'
        fo.write(fill_mets)
        
        while id_list:
            fill_mets = f'                <mets:fptr FILEID="{id_list.pop(0)}"/>\n'
            fo.write(fill_mets)
        
        fo.write(end_mets)

def configure_sip_info(info_path: str, tar_path: str, id: str, creation_date: str):
    """Configure SIP info.xml"""
    extra_id = f'ID{uuid1()}'
    sha = hashlib.sha256()
    
    with open(tar_path, "rb") as f:
        while True:
            tmp_data = f.read(4000000)
            if not tmp_data:
                break
            sha.update(tmp_data)
    
    with open(info_path, "w", encoding="utf-8") as fo:
        string_info = f'<?xml version="1.0" encoding="UTF-8"?>\n<mets:mets xmlns:mets="http://www.loc.gov/METS/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/METS/ http://schema.arkivverket.no/METS/info.xsd" PROFILE="http://xml.ra.se/METS/RA_METS_eARD.xml" LABEL="{label_entry.get()}" TYPE="SIP" ID="ID{uuid1()}" OBJID="UUID:{id}">\n    <mets:metsHdr CREATEDATE="{creation_date}" RECORDSTATUS="NEW">\n        <mets:agent TYPE="ORGANIZATION" ROLE="ARCHIVIST">\n            <mets:name>{archivist_org_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="ARCHIVIST">\n            <mets:name>{system_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="ARCHIVIST">\n            <mets:name>{system_ver_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="ARCHIVIST">\n            <mets:name>{type_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="CREATOR">\n            <mets:name>{creator_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="OTHER" OTHERROLE="PRODUCER">\n            <mets:name>{producer_org_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="INDIVIDUAL" ROLE="OTHER" OTHERROLE="PRODUCER">\n            <mets:name>{producer_pers_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="OTHER" OTHERROLE="PRODUCER">\n            <mets:name>{producer_software_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="OTHER" OTHERROLE="SUBMITTER">\n            <mets:name>{submitter_org_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="INDIVIDUAL" ROLE="OTHER" OTHERROLE="SUBMITTER">\n            <mets:name>{submitter_pers_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="IPOWNER">\n            <mets:name>{owner_org_combo.get()}</mets:name>\n        </mets:agent>\n        <mets:agent TYPE="ORGANIZATION" ROLE="PRESERVATION">\n            <mets:name>{preserver_entry.get()}</mets:name>\n        </mets:agent>\n        <mets:altRecordID TYPE="SUBMISSIONAGREEMENT">{submission_entry.get()}</mets:altRecordID>\n        <mets:altRecordID TYPE="STARTDATE">{period_start_entry.get()}</mets:altRecordID>\n        <mets:altRecordID TYPE="ENDDATE">{period_end_entry.get()}</mets:altRecordID>\n        <mets:metsDocumentID>info.xml</mets:metsDocumentID>\n    </mets:metsHdr>\n    <mets:fileSec>\n        <mets:fileGrp ID="fgrp001" USE="FILES">\n            <mets:file MIMETYPE="application/x-tar" CHECKSUMTYPE="SHA-256" CREATED="{datetime.fromtimestamp(os.path.getmtime(tar_path)).strftime("%Y-%m-%dT%H:%M:%S+02:00")}" CHECKSUM="{sha.hexdigest()}" USE="Datafile" ID="{extra_id}" SIZE="{os.stat(tar_path).st_size}">\n                <mets:FLocat xlink:href="file:{os.path.basename(tar_path)}" LOCTYPE="URL" xlink:type="simple"/>\n            </mets:file>\n        </mets:fileGrp>\n    </mets:fileSec>\n    <mets:structMap>\n        <mets:div LABEL="Package">\n            <mets:div LABEL="Content Description"/>\n            <mets:div LABEL="Datafiles">\n                <mets:fptr FILEID="{extra_id}"/>\n            </mets:div>\n        </mets:div>\n    </mets:structMap>\n</mets:mets>'
        fo.write(string_info)

def configure_aic_log(log_path: str, aic_id: str, sip_id: str, create_date: str):
    """Configure AIC log.xml"""
    with open(log_path, "w", encoding="utf-8") as fo:
        string_log = f'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<premis:premis xmlns:premis="http://arkivverket.no/standarder/PREMIS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://arkivverket.no/standarder/PREMIS http://schema.arkivverket.no/PREMIS/v2.0/DIAS_PREMIS.xsd" version="2.0">\n  <premis:object xsi:type="premis:file">\n    <premis:objectIdentifier>\n      <premis:objectIdentifierType>NO/RA</premis:objectIdentifierType>\n      <premis:objectIdentifierValue>{sip_id}</premis:objectIdentifierValue>\n    </premis:objectIdentifier>\n    <premis:preservationLevel>\n      <premis:preservationLevelValue>full</premis:preservationLevelValue>\n    </premis:preservationLevel>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>aic_object</premis:significantPropertiesType>\n      <premis:significantPropertiesValue>{aic_id}</premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>createdate</premis:significantPropertiesType>\n      <premis:significantPropertiesValue>{create_date}</premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>archivist_organization</premis:significantPropertiesType>\n      <premis:significantPropertiesValue>{archivist_org_combo.get()}</premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>label</premis:significantPropertiesType>\n      <premis:significantPropertiesValue>{label_entry.get()}</premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:significantProperties>\n      <premis:significantPropertiesType>iptype</premis:significantPropertiesType>\n      <premis:significantPropertiesValue>SIP</premis:significantPropertiesValue>\n    </premis:significantProperties>\n    <premis:objectCharacteristics>\n      <premis:compositionLevel>0</premis:compositionLevel>\n      <premis:format>\n        <premis:formatDesignation>\n          <premis:formatName>tar</premis:formatName>\n        </premis:formatDesignation>\n      </premis:format>\n    </premis:objectCharacteristics>\n    <premis:storage>\n      <premis:storageMedium>Preservation platform ESSArch</premis:storageMedium>\n    </premis:storage>\n    <premis:relationship>\n      <premis:relationshipType>structural</premis:relationshipType>\n      <premis:relationshipSubType>is part of</premis:relationshipSubType>\n      <premis:relatedObjectIdentification>\n        <premis:relatedObjectIdentifierType>NO/RA</premis:relatedObjectIdentifierType>\n        <premis:relatedObjectIdentifierValue>{aic_id}</premis:relatedObjectIdentifierValue>\n      </premis:relatedObjectIdentification>\n    </premis:relationship>\n  </premis:object>\n  <premis:event>\n    <premis:eventIdentifier>\n      <premis:eventIdentifierType>NO/RA</premis:eventIdentifierType>\n      <premis:eventIdentifierValue>{uuid1()}</premis:eventIdentifierValue>\n    </premis:eventIdentifier>\n    <premis:eventType>20000</premis:eventType>\n    <premis:eventDateTime>{create_date}</premis:eventDateTime>\n    <premis:eventDetail>Created log circular</premis:eventDetail>\n    <premis:eventOutcomeInformation>\n      <premis:eventOutcome>0</premis:eventOutcome>\n      <premis:eventOutcomeDetail>\n        <premis:eventOutcomeDetailNote>Success to create logfile</premis:eventOutcomeDetailNote>\n      </premis:eventOutcomeDetail>\n    </premis:eventOutcomeInformation>\n    <premis:linkingAgentIdentifier>\n      <premis:linkingAgentIdentifierType>NO/RA</premis:linkingAgentIdentifierType>\n      <premis:linkingAgentIdentifierValue>{USERNAME}</premis:linkingAgentIdentifierValue>\n    </premis:linkingAgentIdentifier>\n    <premis:linkingObjectIdentifier>\n      <premis:linkingObjectIdentifierType>NO/RA</premis:linkingObjectIdentifierType>\n      <premis:linkingObjectIdentifierValue>{sip_id}</premis:linkingObjectIdentifierValue>\n    </premis:linkingObjectIdentifier>\n  </premis:event>\n</premis:premis>'
        fo.write(string_log)

def main_func():
    """Main package creation function"""
    tabview.set(3)
    PROGRESS_BAR.start()
    
    log("=" * 60)
    log("Archive Package Creator - Linux Version")
    log("=" * 60)
    
    try:
        sip_id = uuid1()
        log(f"SIP ID: {sip_id}")
        
        # Find output folder
        output_folder = 1
        while os.path.isdir(f'./{output_folder}'):
            output_folder += 1
        output_folder = f'./{output_folder}'
        tarfile = f'{output_folder}/{sip_id}/content/{sip_id}'
        
        log(f"Output: {output_folder}")
        log("\n--- Building Directory Structure ---")
        
        # Build directory structure
        os.makedirs(f'{output_folder}/{sip_id}/administrative_metadata/repository_operations')
        os.makedirs(f'{output_folder}/{sip_id}/descriptive_metadata')
        os.makedirs(f'{tarfile}/administrative_metadata')
        os.makedirs(f'{tarfile}/descriptive_metadata')
        os.makedirs(f'{tarfile}/content')
        log("  ✓ Directories created")
        
        # Copy template files
        log("Copying template files...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(script_dir, "template_files")
        
        if not os.path.exists(template_dir):
            raise FileNotFoundError(f"Template directory not found: {template_dir}")
        
        shutil.copy(os.path.join(template_dir, "mets.xsd"), f'{tarfile}/mets.xsd')
        shutil.copy(os.path.join(template_dir, "DIAS_PREMIS.xsd"), f'{tarfile}/administrative_metadata/DIAS_PREMIS.xsd')
        log("  ✓ Templates copied")
        
        # Copy optional metadata
        if descriptive_path_label.cget("text"):
            log("Copying descriptive metadata...")
            shutil.copytree(os.path.abspath(descriptive_path_label.cget("text")), 
                          f'{tarfile}/descriptive_metadata', 
                          copy_function=shutil.copy, 
                          dirs_exist_ok=True)
            log("  ✓ Descriptive metadata copied")
        
        if administrative_path_label.cget("text"):
            log("Copying administrative metadata...")
            shutil.copytree(os.path.abspath(administrative_path_label.cget("text")), 
                          f'{tarfile}/administrative_metadata', 
                          copy_function=shutil.copy, 
                          dirs_exist_ok=True)
            log("  ✓ Administrative metadata copied")
        
        # Zone 1 - ETP Processing
        log("\n--- Zone 1: ETP Processing ---")
        
        log("Creating SIP log...")
        configure_sip_log(f'{tarfile}/log.xml', str(sip_id), datetime.now().strftime("%Y-%m-%dT%H:%M:%S+02:00"))
        log("  ✓ SIP log created")
        
        # Gather file information
        info_dict = gather_file_info(tarfile, os.path.basename(tarfile))
        content_info = gather_file_info(content_path_label.cget("text"), f'{os.path.basename(tarfile)}/content')
        info_dict.update(content_info)
        
        log("Creating PREMIS metadata...")
        configure_sip_premis(f'{tarfile}/administrative_metadata/premis.xml', str(sip_id), info_dict)
        log("  ✓ PREMIS created")
        
        log("Creating METS metadata...")
        configure_sip_mets(f'{tarfile}/mets.xml', str(sip_id), 
                          datetime.now().strftime("%Y-%m-%dT%H:%M:%S+02:00"), 
                          f'{tarfile}/administrative_metadata/premis.xml', 
                          info_dict)
        log("  ✓ METS created")
        
        pack_sip(tarfile, str(sip_id), content_path_label.cget("text"))
        
        log("Creating info.xml...")
        configure_sip_info(f'{output_folder}/info.xml', f'{tarfile}.tar', str(sip_id), 
                          datetime.now().strftime("%Y-%m-%dT%H:%M:%S+02:00"))
        log("  ✓ Info.xml created")
        
        # Zone 2 - ETA Processing
        log("\n--- Zone 2: ETA Processing ---")
        aic_id = uuid1()
        log(f"AIC ID: {aic_id}")
        
        os.rename(output_folder, f'./{aic_id}')
        log(f"  ✓ Renamed to: {aic_id}")
        
        configure_aic_log(f'./{aic_id}/{sip_id}/log.xml', str(aic_id), str(sip_id), 
                         datetime.now().strftime("%Y-%m-%dT%H:%M:%S+02:00"))
        log("  ✓ AIC log created")
        
        PROGRESS_BAR.stop()
        log("\n" + "=" * 60)
        log("✓ PROCESS COMPLETE!")
        log(f"Package: {aic_id}")
        log("=" * 60)
        
        customtkinter.CTkButton(tabview.tab(3), text="Finish", 
                               command=lambda: sys.exit()).grid(row=5, column=0, columnspan=5, sticky="NSEW")
        
    except Exception as e:
        error_details = traceback.format_exc()
        with open("./error_log.txt", "w", encoding="utf-8") as fo:
            fo.write(error_details)
        
        PROGRESS_BAR.stop()
        log("\n" + "=" * 60)
        log("❌ ERROR: Process Failed")
        log("=" * 60)
        log(f"Error: {str(e)}")
        log("\nFull error details saved to: error_log.txt")
        log("=" * 60)
        
        messagebox.showerror("Error", f"Package creation failed:\n\n{str(e)}\n\nCheck error_log.txt for details.")

def log(message: str):
    """Log message to the output textbox"""
    LOG_BOX.insert(tkinter.END, f'[{datetime.now().strftime("%d/%m/%y - %H:%M:%S")}]: {message}\n')
    LOG_BOX.see(tkinter.END)
    window.update()

def combo_helper(element: customtkinter.CTkComboBox, lst: list):
    """Filter combo box values based on current input"""
    element.configure(values=[i for i in lst if element.get().lower() in i.lower()])

def set_username():
    """Change the username"""
    global USERNAME
    val = customtkinter.CTkInputDialog(title=' ', text='Set your username:').get_input()
    USERNAME = val if val else USERNAME
    menu.entryconfig(0, label=f'Username: {USERNAME}')

def configure_grid(colsize: int, rowsize: int, widget):
    """Initialize grid for a widget"""
    for col in range(colsize):
        widget.columnconfigure(col, weight=1, pad=0)
    for row in range(rowsize):
        widget.rowconfigure(row, weight=1, pad=0)

# Initialize main window
customtkinter.set_default_color_theme("blue")
customtkinter.set_appearance_mode("dark")
window = customtkinter.CTk()
window.title("Archive Package Creator - Linux")
window.geometry('{width}x{height}+{pos_right}+{pos_down}'.format(
    width=(window.winfo_screenwidth() // 2)+(window.winfo_screenwidth() // 3), 
    height=(window.winfo_screenheight() // 2)+(window.winfo_screenheight() // 3), 
    pos_right=(window.winfo_screenwidth() // 2)-((5*window.winfo_screenwidth()) // 12), 
    pos_down=(window.winfo_screenheight() // 2)-((5*window.winfo_screenheight()) // 12)
))

# Create tabview
tabview = customtkinter.CTkTabview(master=window, state="disabled")
for i in range(1,4):
    tabview.add(i)
tabview.pack(anchor=tkinter.CENTER, fill=tkinter.BOTH, expand=True, padx=10, pady=10)

# Configure tab 1 - File Selection
configure_grid(14,11,tabview.tab(1))

content_path_label = customtkinter.CTkLabel(tabview.tab(1), text="", fg_color="grey", corner_radius=8)
customtkinter.CTkButton(tabview.tab(1), text="Browse Content", 
                       command=lambda: browse_files(content_path_label)).grid(row=1, column=12, columnspan=1, sticky="NSEW")

descriptive_path_label = customtkinter.CTkLabel(tabview.tab(1), text="", fg_color="grey", corner_radius=8)
customtkinter.CTkButton(tabview.tab(1), text="Browse Descriptive Metadata (optional)", 
                       command=lambda: browse_files(descriptive_path_label)).grid(row=4, column=12, columnspan=1, sticky="NSEW")

administrative_path_label = customtkinter.CTkLabel(tabview.tab(1), text="", fg_color="grey", corner_radius=8)
customtkinter.CTkButton(tabview.tab(1), text="Browse Administrative Metadata (optional)", 
                       command=lambda: browse_files(administrative_path_label)).grid(row=7, column=12, columnspan=1, sticky="NSEW")

customtkinter.CTkButton(tabview.tab(1), text="Continue", 
                       command=lambda: tabview.set(2) if content_path_label.cget("text") 
                       else messagebox.showerror("Error", "No content path specified.")).grid(row=10, column=0, columnspan=14, sticky="NSEW")

content_path_label.grid(row=1, column=1, columnspan=9, sticky="NSEW")
descriptive_path_label.grid(row=4, column=1, columnspan=9, sticky="NSEW")
administrative_path_label.grid(row=7, column=1, columnspan=9, sticky="NSEW")

# Configure tab 2 - Metadata Entry
configure_grid(7,8,tabview.tab(2))

TEXT_LIST = [StringVar(tabview.tab(2), name=f'{i}') for i in range(16)]

frame1 = customtkinter.CTkFrame(tabview.tab(2))
frame1.grid(row=1, column=1, columnspan=2, rowspan=2, sticky="NSEW")
configure_grid(6,8,frame1)

frame2 = customtkinter.CTkFrame(tabview.tab(2))
frame2.grid(row=1, column=4, columnspan=2, rowspan=2, sticky="NSEW")
configure_grid(6,6,frame2)

frame3 = customtkinter.CTkFrame(tabview.tab(2))
frame3.grid(row=4, column=1, columnspan=2, rowspan=2, sticky="NSEW")
configure_grid(6,5,frame3)

frame4 = customtkinter.CTkFrame(tabview.tab(2))
frame4.grid(row=4, column=4, columnspan=2, rowspan=2, sticky="NSEW")
configure_grid(6,4,frame4)

customtkinter.CTkButton(tabview.tab(2), text="Create Dias Package", 
                       command=lambda: threading.Thread(target=main_func, daemon=True).start() 
                       if all(len(i.get()) != 0 for i in TEXT_LIST) 
                       else messagebox.showerror("Error", "All input fields require input.")).grid(row=7, column=0, columnspan=7, sticky="NSEW")

# Frame 1 - System Info
customtkinter.CTkLabel(master=frame1, text="Label:", text_color="white", corner_radius=4, anchor='e').grid(row=1, column=1, sticky="EW")
label_entry = customtkinter.CTkEntry(master=frame1, textvariable=TEXT_LIST[4], corner_radius=4)
label_entry.grid(row=1, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame1, text="System:", text_color="white", corner_radius=4, anchor='e').grid(row=2, column=1, sticky="EW")
system_combo = customtkinter.CTkComboBox(master=frame1, variable=TEXT_LIST[0], corner_radius=4, values=SYSTEM_LIST)
system_combo.grid(row=2, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame1, text="System Version:", text_color="white", corner_radius=4, anchor='e').grid(row=3, column=1, sticky="EW")
system_ver_entry = customtkinter.CTkEntry(master=frame1, textvariable=TEXT_LIST[1], corner_radius=4)
system_ver_entry.grid(row=3, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame1, text="Submission Agreement:", text_color="white", corner_radius=4, anchor='e').grid(row=4, column=1, sticky="EW")
submission_entry = customtkinter.CTkEntry(master=frame1, textvariable=TEXT_LIST[2], corner_radius=4)
submission_entry.grid(row=4, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame1, text="Archivist System Type:", text_color="white", corner_radius=4, anchor='e').grid(row=5, column=1, sticky="EW")
type_combo = customtkinter.CTkComboBox(master=frame1, variable=TEXT_LIST[5], corner_radius=4, values=["SIARD", "NOARK-5", "Postjournaler", "Annet"])
type_combo.grid(row=5, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame1, text="Period Start:", text_color="white", corner_radius=4, anchor='e').grid(row=6, column=1, sticky="EW")
period_start_entry = customtkinter.CTkEntry(master=frame1, textvariable=TEXT_LIST[10], corner_radius=4)
period_start_entry.grid(row=6, column=2, sticky="EW")

customtkinter.CTkLabel(master=frame1, text="Period End:", text_color="white", corner_radius=4, anchor='e').grid(row=6, column=3, sticky="EW")
period_end_entry = customtkinter.CTkEntry(master=frame1, textvariable=TEXT_LIST[11], corner_radius=4)
period_end_entry.grid(row=6, column=4, sticky="EW")

# Frame 2 - Organizations
customtkinter.CTkLabel(master=frame2, text="Owner Organization:", text_color="white", corner_radius=4, anchor='e').grid(row=1, column=1, sticky="EW")
owner_org_combo = customtkinter.CTkComboBox(master=frame2, variable=TEXT_LIST[6], corner_radius=4, values=MUNICIPALITY_LIST)
owner_org_combo.grid(row=1, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame2, text="Archivist Organization:", text_color="white", corner_radius=4, anchor='e').grid(row=2, column=1, sticky="EW")
archivist_org_combo = customtkinter.CTkComboBox(master=frame2, variable=TEXT_LIST[3], corner_radius=4, values=MUNICIPALITY_LIST)
archivist_org_combo.grid(row=2, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame2, text="Submitter Organization:", text_color="white", corner_radius=4, anchor='e').grid(row=3, column=1, sticky="EW")
submitter_org_combo = customtkinter.CTkComboBox(master=frame2, variable=TEXT_LIST[12], corner_radius=4, values=MUNICIPALITY_LIST)
submitter_org_combo.grid(row=3, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame2, text="Submitter Person:", text_color="white", corner_radius=4, anchor='e').grid(row=4, column=1, sticky="EW")
submitter_pers_entry = customtkinter.CTkEntry(master=frame2, textvariable=TEXT_LIST[13], corner_radius=4)
submitter_pers_entry.grid(row=4, column=2, columnspan=3, sticky="EW")

# Frame 3 - Producer Info
customtkinter.CTkLabel(master=frame3, text="Producer Organization:", text_color="white", corner_radius=4, anchor='e').grid(row=1, column=1, sticky="EW")
producer_org_entry = customtkinter.CTkEntry(master=frame3, textvariable=TEXT_LIST[7], corner_radius=4)
producer_org_entry.grid(row=1, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame3, text="Producer Person:", text_color="white", corner_radius=4, anchor='e').grid(row=2, column=1, sticky="EW")
producer_pers_entry = customtkinter.CTkEntry(master=frame3, textvariable=TEXT_LIST[8], corner_radius=4)
producer_pers_entry.grid(row=2, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame3, text="Producer Software:", text_color="white", corner_radius=4, anchor='e').grid(row=3, column=1, sticky="EW")
producer_software_entry = customtkinter.CTkEntry(master=frame3, textvariable=TEXT_LIST[9], corner_radius=4)
producer_software_entry.grid(row=3, column=2, columnspan=3, sticky="EW")

# Frame 4 - Creator & Preserver
customtkinter.CTkLabel(master=frame4, text="Creator:", text_color="white", corner_radius=4, anchor='e').grid(row=1, column=1, sticky="EW")
creator_entry = customtkinter.CTkEntry(master=frame4, textvariable=TEXT_LIST[14], corner_radius=4)
creator_entry.grid(row=1, column=2, columnspan=3, sticky="EW")

customtkinter.CTkLabel(master=frame4, text="Preserver:", text_color="white", corner_radius=4, anchor='e').grid(row=2, column=1, sticky="EW")
preserver_entry = customtkinter.CTkEntry(master=frame4, textvariable=TEXT_LIST[15], corner_radius=4)
preserver_entry.grid(row=2, column=2, columnspan=3, sticky="EW")

# Bind filtering functions
system_combo.bind('<KeyRelease>', lambda _: combo_helper(system_combo, SYSTEM_LIST))
type_combo.bind('<KeyRelease>', lambda _: combo_helper(type_combo, ["SIARD", "NOARK-5", "Postjournaler", "Annet"]))
owner_org_combo.bind('<KeyRelease>', lambda _: combo_helper(owner_org_combo, MUNICIPALITY_LIST))
archivist_org_combo.bind('<KeyRelease>', lambda _: combo_helper(archivist_org_combo, MUNICIPALITY_LIST))
submitter_org_combo.bind('<KeyRelease>', lambda _: combo_helper(submitter_org_combo, MUNICIPALITY_LIST))

# Configure tab 3 - Progress & Log
configure_grid(5,6,tabview.tab(3))

PROGRESS_BAR = customtkinter.CTkProgressBar(tabview.tab(3), mode="indeterminate")
LOG_BOX = customtkinter.CTkTextbox(tabview.tab(3), wrap="none", font=("",20))

LOG_BOX.grid(row=1, column=1, columnspan=3, rowspan=3, sticky="NSEW")
PROGRESS_BAR.grid(row=4, column=1, columnspan=3, sticky="EW")

# Add menubar
menu = Menu(master=window)
menu.add_command(label=f'Username: {USERNAME}', command=set_username)
menu.add_command(label='Import mets.xml Metadata', 
                command=lambda: import_metadata(filedialog.askopenfile(initialdir="./", 
                                                                       title="Choose metadata file", 
                                                                       filetypes=[("XML files", "*.xml")])))
window.config(menu=menu)

# Run application
window.mainloop()
