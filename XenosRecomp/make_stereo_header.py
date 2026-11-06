"""stereo_header.py: the empty view macros into XenosRecomp's shader_common.h, and shader_common_stereo.h made from it
(multiview: the 2D texture heap as arrays sampled at the view's layer, the per-eye clip shift)."""
import re
P = r'H:\Xerenge\XenosRecomp\XenosRecomp\shader_common.h'
S = r'H:\Xerenge\XenosRecomp\XenosRecomp\shader_common_stereo.h'
s = open(P, 'rb').read().decode('utf-8')
nl = '\r\n' if '\r\n' in s else '\n'
head = '#define SHADER_COMMON_H_INCLUDED' + nl
assert s.count(head) == 1
old_defaults = (nl + '// Xerenge VR: the view of a multiview (stereo) draw; empty here, set by shader_common_stereo.h.' + nl +
                '#ifndef XERENGE_VIEW_ID_PARAM' + nl + '#define XERENGE_VIEW_ID_PARAM' + nl + '#define XERENGE_VIEW_ID_SET' + nl +
                '#define XERENGE_VIEW_POSITION(p)' + nl + '#endif' + nl)
# Screen-space draws (the viewport transform off: PA_CL_VTE_CNTL's scale and offset bits clear): the position is in the
# target's pixels and z goes to the depth buffer as it is. The renderer sets shared byte 336 for them, with the pixels'
# scale and offset into clip space (340-352) and z's (356, 360). Burnout's billboard smoke, glass, debris and explosion
# smoke are drawn so (sub_8214C118: pixels, z = 0.5 / distance): taken as clip space they all fell off the screen.
screen = ('#define XERENGE_SCREEN_TO_CLIP(p) (p).xy = (p).xy * asfloat(uint2(XENOS_SHARED_UINT(340), '
          'XENOS_SHARED_UINT(344))) + asfloat(uint2(XENOS_SHARED_UINT(348), XENOS_SHARED_UINT(352))) * (p).w; '
          '(p).z = (p).z * asfloat(XENOS_SHARED_UINT(356)) + asfloat(XENOS_SHARED_UINT(360)) * (p).w;')
defaults = (nl + '// Xerenge: screen-space draws into clip space (shared bytes 336-360, set by the renderer).' + nl + screen +
            nl + '// Xerenge VR: the view of a multiview (stereo) draw; empty here, set by shader_common_stereo.h.' + nl +
            '#ifndef XERENGE_VIEW_ID_PARAM' + nl + '#define XERENGE_VIEW_ID_PARAM' + nl + '#define XERENGE_VIEW_ID_SET' + nl +
            '#ifdef __spirv__' + nl +
            '#define XERENGE_VIEW_POSITION(p) if (XENOS_SHARED_UINT(336) != 0) { XERENGE_SCREEN_TO_CLIP(p) }' + nl +
            '#else' + nl + '#define XERENGE_VIEW_POSITION(p)' + nl + '#endif' + nl + '#endif' + nl)
if old_defaults in s:
    s = s.replace(old_defaults, defaults)
    open(P, 'wb').write(s.encode('utf-8'))
elif 'XERENGE_VIEW_ID_PARAM' not in s:
    s = s.replace(head, head + defaults)
    open(P, 'wb').write(s.encode('utf-8'))
assert defaults in s

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
    '// Screen-space draws (shared byte 336) into clip space, each eye shifted by its clip shift times the draw\'s',
    '// depth per unit of z (shared byte 332: Burnout\'s z is 0.5 / distance, so 2); other geometry at w 1 (the',
    '// interface) stays put; perspective geometry moves by the clip shift.',
    '#define XERENGE_VIEW_POSITION(p) if (XENOS_SHARED_UINT(336) != 0) { float xerengeZ = (p).z; \\',
    '    XERENGE_SCREEN_TO_CLIP(p) (p).x += XERENGE_EYE_SHIFT * asfloat(XENOS_SHARED_UINT(332)) * xerengeZ * (p).w; } \\',
    '    else if (abs((p).w - 1.0) > (1.0 / 1024.0)) (p).x += XERENGE_EYE_SHIFT;',
    '#else',
    '#define XERENGE_VIEW_ID_PARAM',
    '#define XERENGE_VIEW_ID_SET',
    '#define XERENGE_EYE_SHIFT 0.0',
    '#define XERENGE_VIEW_POSITION(p)',
    '#endif',
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
