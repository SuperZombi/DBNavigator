window.addEventListener("load", _=>{
	init_checks();
	init_actions();
})

function init_checks(){
	let checked_amount = 0;
	let checks = document.querySelectorAll(".tab-content table input[type='checkbox']")
	checks.forEach(e=>{
		e.onchange = _=>{
			if (e.checked){
				checked_amount++;
			} else{
				checked_amount--;
			}

			if (checked_amount > 0){
				document.querySelector("#actions").classList.add("show")
				if (checked_amount > 1){
					document.querySelector("#actions #edit").disabled = true;
				} else{
					document.querySelector("#actions #edit").disabled = false;
				}
			} else{
				document.querySelector("#actions").classList.remove("show")
			}
		}
	})
}
function init_actions(){
	document.querySelector("#actions #edit").onclick = _=>{
		let checkbox = document.querySelector(".tab-content table input[type='checkbox']:checked")
		window.location.href = `edit?row=${checkbox.getAttribute("rowid")}`
	}
	document.querySelector("#actions #delete").onclick = _=>{
		let selected = document.querySelectorAll(".tab-content table input[type='checkbox']:checked")
		document.querySelector("#delete-dialog #delete-amount").innerHTML = selected.length;
	}
	document.querySelector("#delete-dialog #confirm-delete").onclick = _=>{
		let selected = document.querySelectorAll(".tab-content table input[type='checkbox']:checked")
		let rows = Array.from(selected).map(e=>{return e.getAttribute("rowid")})
		const searchParams = new URLSearchParams({rows: rows, redirect: window.location.href});
		window.location.href = `delete?${searchParams.toString()}`
	}
}
