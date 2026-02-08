[out:json][timeout:250];
area[name="Barcelona"]["admin_level"="6"]->.barcelona;
(
way(area.barcelona)["highway"~"pedestrian|cycleway|footway"]["smoothness"~"excellent|good"]["bicycle"!="no"]["inline_skates"!="no"];
way(area.barcelona)["highway"~"cycleway|footway|pedestrian"]["surface"="asphalt"]["bicycle"!="no"]["inline_skates"!="no"];
);
out geom;
