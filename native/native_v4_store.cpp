// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Fiber Continuity contributors.
// Native API pin: ScrollPrize/villa@c3d9da6fe42c3bb46fd2603ca060845d843296c3.
// Dependencies: vc_objects, vc_geometry and their native catalog/system libraries.
// Points are stored XYZ annotation voxels; physical micrometre metadata stays metadata.
// coordinates.volume_uuid is the input volume's metadata.json volume.id, verbatim.
#include <vc_object_store/geometry/Geometry.hpp>
#include <vc_object_store/objects/FiberJson.hpp>
#include <vc_object_store/objects/GeometryCoordinates.hpp>
#include <vc_object_store/objects/ObjectStore.hpp>
#include <vc_object_store/store/GeometryViews.hpp>
#include <nlohmann/json.hpp>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

using Json=nlohmann::json;
using vc::geometry::Fiber;
using vc::objects::ObjectStore;
namespace fs=std::filesystem;
static void need(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
struct Input {
    vc::objects::GeometrySource native;
    Fiber expected;
    Json metadata;
    std::string revision;
};

int main(int argc,char** argv){
    try{
        need(argc==3,"usage: native_v4_store INPUT.json OUTPUT.vcobj");
        std::ifstream stream(argv[1]);need(bool(stream),"input JSON read failed");
        Json documents;stream>>documents;
        if(documents.is_object())documents=Json::array({documents});
        need(documents.is_array()&&!documents.empty(),"input must be a V4 fiber or a nonempty V4 fiber array");
        std::vector<Input> inputs;
        for(const auto& document:documents){
            need(document.at("type")=="vc3d_fiber"&&document.at("version")==4,"native V4 fiber required");
            for(const auto& control:document.at("control_points"))
                need(control.is_object()&&control.size()==1&&control.contains("position"),"polyline CLI requires position-only controls");
            for(const auto& point:document.at("line_points"))
                need(point.is_array()&&point.size()==3,"dense line points must be XYZ triplets");
            for(const char* relation:{"branches","adjacent_branches"})
                need(!document.contains(relation)||document.at(relation).empty(),"fiber relationships require native graph ingestion");
            Input input;input.native=vc::objects::decodeFiberJson(document.dump());
            input.expected=std::get<Fiber>(vc::geometry::decode(input.native.geometry));
            const auto coordinates=vc::objects::sourceGeometryCoordinates(input.native.source);
            need(!coordinates.at("volume_uuid").is_null()&&!coordinates.at("scale_factor").is_null(),"complete input volume.id and scale_factor required");
            auto source=input.native.source;vc::objects::eraseSourceGeometryCoordinates(source);
            input.metadata={{"coordinates",coordinates},{"source",source}};
            input.native.object.meta=input.metadata.dump();
            inputs.push_back(std::move(input));
        }
        const fs::path destination=argv[2];
        need(destination.extension()==".vcobj","output extension must be .vcobj");
        need(!fs::exists(destination),"output already exists");
        if(!destination.parent_path().empty())fs::create_directories(destination.parent_path());
        std::string store_id;
        {
            vc::objects::OpenOptions options;options.author="native-v4-cli";
            auto store=ObjectStore::create(destination,options);
            {
                vc::objects::VersionSelection expected;
                for(const auto& input:inputs)expected.emplace(input.native.object.uuid,std::nullopt);
                auto tx=store.write(expected);
                for(auto& input:inputs){
                    const auto uid=store.upsertObject(tx,input.native.object);
                    need(uid==input.native.object.uuid,"native object ID changed");
                    input.revision=store.putGeometry(tx,uid,input.native.geometry);
                }
                tx.commit();
            }
            store.checkpoint();{auto read=store.read();store_id=store.uuid(read);}
        }
        int64_t count=0;double max_frame_error=0;
        {
            vc::objects::OpenOptions options;options.readOnly=true;
            auto store=ObjectStore::open(destination,options);auto read=store.read();
            need(store.uuid(read)==store_id,"store ID changed after closed reopen");
            vc::objects::GeometrySnapshot snapshot(store);
            for(const auto& input:inputs){
                const auto record=store.objectByUuid(read,input.native.object.uuid);
                need(record.has_value(),"native fiber missing");
                need(Json::parse(record->meta)==input.metadata,"source metadata or frame changed");
                need(record->fiber&&input.native.object.fiber&&record->fiber->family==input.native.object.fiber->family&&record->fiber->manualFamily==input.native.object.fiber->manualFamily,"native family changed");
                auto view=snapshot.fiber(record->uuid,input.revision);const auto loaded=view.load();
                need(loaded.linePoints==input.expected.linePoints&&loaded.controlPoints==input.expected.controlPoints,"native point values or order changed");
                need(loaded.controlPointIds==input.expected.controlPointIds,"native control IDs changed");
                need(loaded.length()==input.expected.length(),"native polyline length changed");
                const auto volume=input.metadata.at("coordinates").at("volume_uuid").get<std::string>();
                const double to_volume=vc::objects::geometryScaleToFrame(input.metadata,volume);
                auto frame_view=view.viewTransformedAt(volume,1);
                need(frame_view.targetVolume()==volume&&frame_view.targetScale()==1,"target frame changed");
                const auto transformed=frame_view.points("line_points",0,loaded.linePoints.size());
                for(size_t i=0;i<transformed.size();++i)for(int axis=0;axis<3;++axis){
                    const double error=std::abs(transformed[i][axis]-loaded.linePoints[i][axis]*to_volume);
                    max_frame_error=std::max(max_frame_error,error);
                    need(error<=1e-9*std::max(1.,std::abs(transformed[i][axis])),"native frame conversion changed");
                }
                count+=loaded.linePoints.size();
            }
            snapshot.close();
        }
        std::cout<<Json{{"format_roundtrip","passed"},{"native_v4_codec","passed"},
                       {"closed_reopen","passed"},{"immutable_typed_load","passed"},
                       {"points_order_control_IDs_source_metadata","preserved"},
                       {"fiber_count",inputs.size()},{"point_count",count},
                       {"max_native_frame_abs_error_vox",max_frame_error}}.dump(2)<<'\n';
        return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
