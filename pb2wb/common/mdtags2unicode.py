ALLOWED_CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

CONVERSION_CHARS = {
  'B': " 𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵",
  'I': " 𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯0123456789",
  'SI': " ABCDEFGHIJKLMNOPQRSTUVWXYZabcdₑfgₕᵢⱼₖₗₘₙₒₚqᵣₛₜᵤᵥwₓyz0123456789",
  'SS': " ᴬᴮᶜᴰᴱᶠᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾQᴿˢᵀᵁⱽᵂˣʸᶻᵃᵇᶜᵈᵉᶠᵍʰᶦʲᵏˡᵐⁿᵒᵖᑫʳˢᵗᵘᵛʷˣʸᶻ⁰¹²³⁴⁵⁶⁷⁸⁹"
}

def mdtags2unicode(text):
  current_pos = 0
  convert_chars = None
  tag_name = ''
  last_tag_name = ''
  inside_tag_name = False
  tag_type_start = True
  result = ''

  for ch in text:
    if inside_tag_name:
      if ch == '/' or ch == 'E':
        if tag_name:
          raise ValueError(f'Invalid tag char in position {current_pos} character ({ch}).')
        else:
          tag_type_start = False
      elif ch == '{':
        raise ValueError(f'Invalid tag char in position {current_pos} character ({ch}).')
      elif ch == '}':
        inside_tag_name = False
        if tag_type_start:
          if tag_name in CONVERSION_CHARS:
            convert_chars = CONVERSION_CHARS[tag_name]
          else:
            raise ValueError(f'Invalid tag name ({tag_name}) in position {current_pos}.')
        else:
          if tag_name != last_tag_name:
            raise ValueError(f'Invalid tag end in position {current_pos} received tag {tag_name} but expected {last_tag_name}.')
          else:
            tag_name = None
      else:
        tag_name += ch
    else:
      if ch == '{':
        inside_tag_name = True
        tag_type_start = True
        last_tag_name = tag_name
        tag_name = ''
        convert_chars = None
      else:
        if convert_chars:
          location = ALLOWED_CHARS.find(ch)
          if location == -1:
            raise ValueError(f'Not allowed character to convert in position {current_pos} character ({ch}).')
          result += convert_chars[location]
        else:
          result += ch
    current_pos += 1

  return result

TEXT = "aa  {B} aa{/B} {I}bb{/I} {/SI}"
print(TEXT)
print(mdtags2unicode(TEXT))
