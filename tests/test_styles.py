"""Tests for the centralized CSS-layer resolution/rendering in ebk.core.styles."""

from ebk.core.styles import (
    CssLayer,
    resolve_css_layers,
    render_css_links,
    render_inline_style_block,
    load_default_css,
    default_css_enabled,
)


def _init_project(tmp_path, config=None):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / '01.md').write_text('# T\n')
    return config or {}


def test_default_css_is_first_layer_by_default(tmp_path):
    config = _init_project(tmp_path)
    (tmp_path / 'custom.css').write_text('body { color: red; }\n')
    config['default_css'] = ['custom.css']

    layers = resolve_css_layers(str(tmp_path), config)

    assert [l.name for l in layers] == ['default.css', 'custom.css']
    assert layers[0].source == 'default'
    assert layers[1].source == 'project'


def test_include_default_false_suppresses_base_layer(tmp_path):
    config = _init_project(tmp_path)
    (tmp_path / 'custom.css').write_text('body { color: red; }\n')
    config['default_css'] = ['custom.css']

    layers = resolve_css_layers(str(tmp_path), config, include_default=False)

    assert [l.name for l in layers] == ['custom.css']


def test_styles_config_include_default_false_suppresses_base_layer(tmp_path):
    config = _init_project(tmp_path)
    config['styles'] = {'include_default': False}

    layers = resolve_css_layers(str(tmp_path), config)

    assert layers == []
    assert default_css_enabled(config) is False


def test_tailwind_layer_lands_between_default_and_project_css(tmp_path):
    config = _init_project(tmp_path)
    (tmp_path / 'custom.css').write_text('body { color: red; }\n')
    config['default_css'] = ['custom.css']
    tailwind_layer = CssLayer(name='tailwind.css', text='.text-red-500{color:red}', source='tailwind')

    layers = resolve_css_layers(str(tmp_path), config, tailwind_css=tailwind_layer)

    assert [l.name for l in layers] == ['default.css', 'tailwind.css', 'custom.css']


def test_legacy_assets_css_path_fallback_resolves(tmp_path):
    config = _init_project(tmp_path)
    (tmp_path / 'assets' / 'css').mkdir(parents=True)
    (tmp_path / 'assets' / 'css' / 'legacy.css').write_text('body { color: blue; }\n')
    config['default_css'] = ['legacy.css']

    layers = resolve_css_layers(str(tmp_path), config)

    names = [l.name for l in layers]
    assert 'legacy.css' in names
    legacy_layer = next(l for l in layers if l.name == 'legacy.css')
    assert 'color: blue' in legacy_layer.text


def test_missing_default_css_entry_warns_and_is_skipped(tmp_path, capsys):
    config = _init_project(tmp_path)
    config['default_css'] = ['nope.css']

    layers = resolve_css_layers(str(tmp_path), config)

    assert [l.name for l in layers] == ['default.css']
    assert 'nope.css' in capsys.readouterr().out


def test_render_css_links_xhtml_self_closing():
    result = render_css_links(['default.css', 'custom.css'], xhtml=True)
    assert '<link rel="stylesheet" type="text/css" href="css/default.css" />' in result
    assert '<link rel="stylesheet" type="text/css" href="css/custom.css" />' in result


def test_render_css_links_html5_not_self_closing():
    result = render_css_links(['default.css'], xhtml=False)
    assert result == '  <link rel="stylesheet" href="css/default.css">'


def test_render_inline_style_block_concatenates_in_order():
    layers = [
        CssLayer(name='a.css', text='body{color:red}', source='project'),
        CssLayer(name='b.css', text='body{color:blue}', source='project'),
    ]
    block = render_inline_style_block(layers)
    assert block.index('color:red') < block.index('color:blue')
    assert 'a.css' in block
    assert 'b.css' in block


def test_load_default_css_reads_shipped_resource():
    layer = load_default_css()
    assert layer.name == 'default.css'
    assert layer.source == 'default'
    assert 'body' in layer.text
