use std::{collections::HashMap, fmt::format};

use r2r;
use futures::{StreamExt, future};
use serde_json::Value;
use tokio::task;
use fltk::{app::scheme, prelude::*};
use sp_domain::*;




#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let ctx = r2r::Context::create()?;
    let mut node = r2r::Node::create(ctx, "rust_ui", "")?;

    let app = fltk::app::App::default();
    let mut wind = fltk::window::Window::default().with_size(1000, 600);
    let mut but = fltk::button::Button::new(160, 255, 80, 40, "Get Items");
    but.set_frame(fltk_theme::widget_themes::OS_DEFAULT_BUTTON_UP_BOX);
    let tree = fltk::tree::Tree::new(5, 10, 190, 240, "");

    let mut t = tree.clone();
    but.set_callback(move |cb| {
        t.hide();
    });

    let widget_theme = fltk_theme::WidgetTheme::new(fltk_theme::ThemeType::Dark);
    widget_theme.apply();
    wind.make_resizable(true);
    wind.end();
    wind.show();


    let sub_state = node.subscribe::<r2r::std_msgs::msg::String>("/testing")?;
    let pub_state = node.create_publisher::<r2r::std_msgs::msg::String>("/testing")?;

    
    tokio::spawn(my_tree(tree, sub_state));
    tokio::spawn(testing(pub_state));




    let handle = std::thread::spawn(move || loop {
        node.spin_once(std::time::Duration::from_millis(100));
    });



   

    app.run().unwrap();

    Ok(())
}


async fn my_tree(
    tree: fltk::tree::Tree, 
    mut sub_state: impl futures::Stream<Item = r2r::std_msgs::msg::String> + Unpin) -> Result<(), serde_json::Error> {
    let mut item_map: std::collections::HashMap<SPPath, fltk::tree::TreeItem> = std::collections::HashMap::new();
        loop {
            let mut tree = tree.clone();
            match sub_state.next().await {
                Some(msg) => {
                    let json: Value = serde_json::from_str(&msg.data)?;
                    let state = SPStateJson::from_json(json)?;
                    let s= state.to_state();
                    let mut sp = s.projection();
                    sp.sort();
                    
                    for (p,v) in sp.state {
                        let new_label = format!("{} -> {}", p.to_string(), v.value().to_string());
                        match item_map.get_mut(&p) {
                            Some(ti) => {
                                ti.set_label(&new_label);
                            },
                            None => {
                                let mut ti = tree.add(&p.to_string()).unwrap();
                                ti.set_label(&new_label);
                                item_map.insert(p.clone(), ti.clone());
                            }
                        }
                    }
                },
                None => break,
            }
            tree.redraw();
            fltk::app::awake();
            
        }
        Ok(())
}



