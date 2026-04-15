#include "dim.h"
#include "generic/utf8_constants.h"

namespace
{

double TypeToScale( int type )
{
	switch( type )
	{
		case DIM_TYPE_ANGLE_3_PNT:
		case DIM_TYPE_ANGLE_4_PNT:
		case DIM_TYPE_ANGLE_EDGE:
		case DIM_TYPE_ANGLE_SRF_SRF:
		case DIM_TYPE_ANGLE_SRF_EDG:
		case DIM_TYPE_ANGLE_EDG_EDG:
		case DIM_TYPE_ANGLE_CORNER: return sim::RAD2DEG_FAC;
	}
	return 1;
}

} // namespace

int DIM::DIM2ID( int type )
{
	switch( type )
	{
		case DIM_TYPE_DISTANCE:
		case DIM_TYPE_X_DISTANCE | DIM_TYPE_Y_DISTANCE | DIM_TYPE_Z_DISTANCE: return 3320;
		case DIM_TYPE_ANGLE_3_PNT:
		case DIM_TYPE_ANGLE_4_PNT:
		case DIM_TYPE_ANGLE_EDGE:
		case DIM_TYPE_ANGLE_SRF_SRF:
		case DIM_TYPE_ANGLE_SRF_EDG:
		case DIM_TYPE_ANGLE_EDG_EDG:
		case DIM_TYPE_ANGLE_CORNER: return 3321;
		case DIM_TYPE_FLATNESS: return 3314;
		case DIM_TYPE_STRAIGHTNESS: return 3313;
		case DIM_TYPE_ROUNDNESS_2D: return 3312;
		case DIM_TYPE_ROUNDNESS_3D: return 3909;
		case DIM_TYPE_GEODESIC_DISTANCE: return 5055;
		case DIM_TYPE_COORDINATE_X:
		case DIM_TYPE_COORDINATE_Y:
		case DIM_TYPE_COORDINATE_Z: return 5524 + type - DIM_TYPE_COORDINATE_X;
		case DIM_TYPE_X_DISTANCE: return 5537;
		case DIM_TYPE_Y_DISTANCE: return 5538;
		case DIM_TYPE_Z_DISTANCE: return 5539;
		case DIM_TYPE_Y_DISTANCE | DIM_TYPE_Z_DISTANCE: return 5540;
		case DIM_TYPE_Z_DISTANCE | DIM_TYPE_X_DISTANCE: return 5541;
		case DIM_TYPE_X_DISTANCE | DIM_TYPE_Y_DISTANCE: return 5542;
		case DIM_TYPE_HYDRAULIC_DIAMETER: return 5598;
	}
	return -1;
}

sim::String DIM::DIM2Unit( int type )
{
	switch( type )
	{
		case DIM_TYPE_DISTANCE:
		case DIM_TYPE_X_DISTANCE | DIM_TYPE_Y_DISTANCE | DIM_TYPE_Z_DISTANCE:
		case DIM_TYPE_FLATNESS:
		case DIM_TYPE_STRAIGHTNESS:
		case DIM_TYPE_ROUNDNESS_2D:
		case DIM_TYPE_ROUNDNESS_3D:
		case DIM_TYPE_GEODESIC_DISTANCE:
		case DIM_TYPE_COORDINATE_X:
		case DIM_TYPE_COORDINATE_Y:
		case DIM_TYPE_COORDINATE_Z:
		case DIM_TYPE_X_DISTANCE:
		case DIM_TYPE_Y_DISTANCE:
		case DIM_TYPE_Z_DISTANCE:
		case DIM_TYPE_Y_DISTANCE | DIM_TYPE_Z_DISTANCE:
		case DIM_TYPE_Z_DISTANCE | DIM_TYPE_X_DISTANCE:
		case DIM_TYPE_X_DISTANCE | DIM_TYPE_Y_DISTANCE:
		case DIM_TYPE_HYDRAULIC_DIAMETER: return "mm";
		case DIM_TYPE_ANGLE_3_PNT:
		case DIM_TYPE_ANGLE_4_PNT:
		case DIM_TYPE_ANGLE_EDGE:
		case DIM_TYPE_ANGLE_SRF_SRF:
		case DIM_TYPE_ANGLE_SRF_EDG:
		case DIM_TYPE_ANGLE_EDG_EDG:
		case DIM_TYPE_ANGLE_CORNER: return UTF8_DEGREE;
	}
	return "N/A";
}

DIM::DIM( uint16_t dim_type, const sim::Array<MPT>& mpts, const double* xwa_value, double set_value,
	double min_value, double max_value, const sim::String& name )
	: DIM( dim_type )
{
	mpt = mpts;

	switch( DimType() )
	{
		case DIM_TYPE_FLATNESS:
		case DIM_TYPE_STRAIGHTNESS:
		case DIM_TYPE_ROUNDNESS_2D:
		case DIM_TYPE_ROUNDNESS_3D: sim::FAssign( xwa, xwa_value, 3 ); break;
	}

	SetSet( set_value );
	SetMin( min_value );
	SetMax( max_value );

	if( name.Size() )
	{
		switch( DimType() )
		{
			case DIM_TYPE_COORDINATE_X:
			case DIM_TYPE_COORDINATE_Y:
			case DIM_TYPE_COORDINATE_Z:
				SetName( sim::PhStr( "#1# - #2#", name, "XYZ"[DimType() - DIM_TYPE_COORDINATE_X] ).C() );
				break;
			default: SetName( name.C() ); break;
		}
	}
}

double DIM::Scale() const { return TypeToScale( DimType() ); }

cmu::Unit DIM::UnitType() const
{
	switch( DimType() )
	{
		case DIM_TYPE_ANGLE_3_PNT:
		case DIM_TYPE_ANGLE_4_PNT:
		case DIM_TYPE_ANGLE_CORNER:
		case DIM_TYPE_ANGLE_EDGE:
		case DIM_TYPE_ANGLE_EDG_EDG:
		case DIM_TYPE_ANGLE_SRF_EDG:
		case DIM_TYPE_ANGLE_SRF_SRF: return cmu::Unit( cmu::UT_ANGLE, cmu::AGU_GRAD );
		default: return cmu::Unit( cmu::UT_LENGTH, cmu::LengthUnit::LU_MILLIMETER );
	}
	return cmu::Unit();
}
