"""stereo_header.py: the empty view macros into XenosRecomp's shader_common.h, and shader_common_stereo.h made from it
(multiview: the 2D texture heap as arrays sampled at the view's layer, the per-eye clip shift)."""
import re
P = r'H:\Xerenge\XenosRecomp\XenosRecomp\shader_common.h'
S = r'H:\Xerenge\XenosRecomp\XenosRecomp\shader_common_stereo.h'
s = open(P, 'rb').read().decode('utf-8')
nl = '\r\n' if '\r\n' in s else '\n'
head = '#define SHADER_COMMON_H_INCLUDED' + nl
assert s.count(head) == 1
defaults = (nl + '// Xerenge VR: the view of a multiview (stereo) draw; empty here, set by shader_common_stereo.h.' + nl +
            '#ifndef XERENGE_VIEW_ID_PARAM' + nl + '#define XERENGE_VIEW_ID_PARAM' + nl + '#define XERENGE_VIEW_ID_SET' + nl +
            '#define XERENGE_VIEW_POSITION(p)' + nl + '#endif' + nl)
if 'XERENGE_VIEW_ID_PARAM' not in s:
    s = s.replace(head, head + defaults)
    open(P, 'wb').write(s.encode('utf-8'))

t = s
prelude = nl.join([
    '',
    '// Xerenge VR: the multiview (stereo) variant of shader_common.h (made from it by stereo_header.py). Each draw',
    '// renders both eyes (SV_ViewID); 2D textures are arrays, an eye a layer where the texture has two (a copy of the',
    '// stereo scene), the one layer for both where it has one. Perspective geometry moves by the eye\'s clip shift',
    '// (shared bytes 320 / 324: left, right).',
    '#define XERENGE_STEREO 1',
    'static uint g_ViewId = 0;',
    '#ifdef __spirv__',
    '#define XERENGE_VIEW_ID_PARAM , in uint iViewId : SV_ViewID',
    '#define XERENGE_VIEW_ID_SET g_ViewId = iViewId;',
    '#define XERENGE_EYE_SHIFT (g_ViewId != 0 ? asfloat(XENOS_SHARED_UINT(324)) : asfloat(XENOS_SHARED_UINT(320)))',
    '#else',
    '#define XERENGE_VIEW_ID_PARAM',
    '#define XERENGE_VIEW_ID_SET',
    '#define XERENGE_EYE_SHIFT 0.0',
    '#endif',
    '#define XERENGE_VIEW_POSITION(p) if (abs((p).w - 1.0) > (1.0 / 1024.0)) (p).x += XERENGE_EYE_SHIFT;',
    ''])
t = t.replace(head, head + prelude)


def rep(old, new, count=1):
    global t
    old = old.replace('\n', nl)
    new = new.replace('\n', nl)
    assert t.count(old) == count, (old, t.count(old))
    t = t.replace(old, new)


rep('[[vk::binding(3, 0)]] Texture2D<float4> g_Texture2DDescriptorHeap[16];',
    '[[vk::binding(3, 0)]] Texture2DArray<float4> g_Texture2DDescriptorHeap[16];')
rep('Texture2D<float4> g_Texture2DDescriptorHeap[] : register(t0, space0);',
    'Texture2DArray<float4> g_Texture2DDescriptorHeap[] : register(t0, space0);')
rep('''uint2 getTexture2DDimensions(Texture2D<float4> texture)
{
    uint2 dimensions;
    texture.GetDimensions(dimensions.x, dimensions.y);
    return dimensions;
}''', '''uint2 getTexture2DDimensions(Texture2DArray<float4> texture)
{
    uint3 dimensions;
    texture.GetDimensions(dimensions.x, dimensions.y, dimensions.z);
    return dimensions.xy;
}''')
rep('    Texture2D<float4> texture = g_Texture2DDescriptorHeap[resourceDescriptorIndex];',
    '    Texture2DArray<float4> texture = g_Texture2DDescriptorHeap[resourceDescriptorIndex];', 3)
rep('''    return texture.Sample(g_SamplerDescriptorHeap[samplerDescriptorIndex], texCoord + offset / getTexture2DDimensions(texture));''',
    '''    return texture.Sample(g_SamplerDescriptorHeap[samplerDescriptorIndex], float3(texCoord + offset / getTexture2DDimensions(texture), g_ViewId));''')
rep('''    return texture.SampleLevel(g_SamplerDescriptorHeap[samplerDescriptorIndex], texCoord + offset / getTexture2DDimensions(texture), 0.0);''',
    '''    return texture.SampleLevel(g_SamplerDescriptorHeap[samplerDescriptorIndex], float3(texCoord + offset / getTexture2DDimensions(texture), g_ViewId), 0.0);''')
# the bicubic fetch (the non-air one: texture.Sample(samplerState, float2(...) / float2(dimensions)))
n = len(re.findall(r'texture\.Sample\(samplerState, (float2\([^)]*\) / float2\(dimensions\))\)', t))
assert n == 4, n
t = re.sub(r'texture\.Sample\(samplerState, (float2\([^)]*\) / float2\(dimensions\))\)',
           r'texture.Sample(samplerState, float3(\1, g_ViewId))', t)
open(S, 'wb').write(t.encode('utf-8'))
print('ok', S)
