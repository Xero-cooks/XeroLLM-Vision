import pytest
from spatial_serializer import UIElement,serialize

def test_native_pixels_and_normalized_centers_are_unambiguous():
 s=serialize([UIElement('Save',(80,200,106,216),.99)],1280,720,'test','now',1)
 assert 'pixel_x:93, pixel_y:208' in s and 'norm_x:073, norm_y:289' in s
 assert 'click_targets="not_inferred"' in s

def test_pixel_centers_are_inside_actual_viewport():
 s=serialize([UIElement('edge',(-2,-2,2600,1500),.9)],1280,720,'t','n',1)
 assert 'pixel_x:1279, pixel_y:719' in s

@pytest.mark.parametrize('w,h',[(0,720),(1280,0),(-1,720)])
def test_nonpositive_dimensions_rejected(w,h):
 with pytest.raises(ValueError):serialize([],w,h,'t','n',1)
