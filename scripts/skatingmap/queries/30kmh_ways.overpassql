[out:json][timeout:250];
area[name="Barcelona"]["admin_level"="6"]->.barcelona;
(
way(area.barcelona)["maxspeed"="30"]["highway"]["bicycle"!="no"]["inline_skates"!="no"];
);
out geom;
